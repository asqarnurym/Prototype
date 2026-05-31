"""
descriptor.py — Generation of visual event descriptions (frames).

[DATA FLOW]
INPUT: Path to local screenshot (.png) and language ("en", "ru").
OUTPUT: Description text (string) no longer than settings.max_description_length.
SENT TO: pipeline/visual/scene_indexer.py (for saving in JSON).

Creates a brief description of the frame via the connected description service.
"""

import logging
import threading
import time

from core.config import settings

logger = logging.getLogger(__name__)

# Retry policy for Vertex AI rate limits
MAX_DESCRIPTION_RETRIES = 4
INITIAL_BACKOFF_SEC = 2.0


def _is_frame_blank(image_path: str, *, darkness_threshold: float = 0.95) -> bool:
    """Return True if the frame is > `darkness_threshold` fraction black/dark pixels."""
    try:
        from PIL import Image

        img = Image.open(image_path).convert("L")  # grayscale
        pixels = list(img.getdata())
        if not pixels:
            return True
        dark_count = sum(1 for p in pixels if p < 25)  # RGB < 25 → nearly black
        return (dark_count / len(pixels)) > darkness_threshold
    except Exception:
        return False  # If we can't read the image, let the model decide


def generate_description(
    image_path: str,
    language: str = "en",
) -> str:
    """
    Generates a brief description of the frame in natural language.

    The description service receives the image directly and:
    - Reads any text on the frame (slides, captions, charts)
    - Understands visual context (diagrams, schemes, photos)
    - Forms a brief description for audio description

    Args:
        image_path: Path to the PNG frame.
        language: Description language ("en" or "ru").

    Returns:
        Frame description in natural language.
    """
    # Skip near-black frames — they contribute no useful audio description
    if _is_frame_blank(image_path):
        logger.info("Scene description skipped [reason=blank_frame image=%s]", image_path)
        return ""  # scene_indexer will filter out empty descriptions

    runtime = settings.description_runtime_info()
    if settings.description_service_configured:
        return _describe_with_model_retry(image_path, language)

    # Fallback without API — minimal placeholder description
    logger.warning(
        "Scene description fallback [reason=not_configured provider=%s model=%s project=%s location=%s auth=%s image=%s]",
        runtime["provider"],
        runtime["model"],
        runtime["project"],
        runtime["location"],
        runtime["auth_mode"],
        image_path,
    )
    return _describe_fallback(language)


_client = None
_client_lock = threading.Lock()


def _get_description_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                from google import genai
                from google.genai import types

                runtime = settings.description_runtime_info()
                logger.info(
                    "Initializing Gemini Vertex client for scene descriptions [sdk=%s model=%s project=%s location=%s auth=%s service_account=%s]",
                    runtime["sdk"],
                    runtime["model"],
                    runtime["project"],
                    runtime["location"],
                    runtime["auth_mode"],
                    runtime["service_account_email"],
                )

                _client = genai.Client(
                    vertexai=True,
                    project=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                    http_options=types.HttpOptions(api_version="v1"),
                )
    return _client


def _describe_with_model_retry(image_path: str, language: str) -> str:
    """Call _describe_with_model, retrying on rate-limit (429) with exponential backoff."""
    last_exc = None
    for attempt in range(MAX_DESCRIPTION_RETRIES):
        try:
            result = _describe_with_model(image_path, language)
            # If the model returned a fallback description and it wasn't a real API error,
            # it might have been an empty response — still worth retrying once
            if result in (_describe_fallback("en"), _describe_fallback("ru")):
                if attempt < 1:  # one retry for empty/filler responses
                    time.sleep(INITIAL_BACKOFF_SEC)
                    continue
            return result
        except Exception as exc:
            last_exc = exc
            _, status_code = _classify_model_error(exc)
            if status_code == 429 and attempt < MAX_DESCRIPTION_RETRIES - 1:
                wait = INITIAL_BACKOFF_SEC * (2 ** attempt)
                logger.warning(
                    "Rate-limited (429) on attempt %d/%d, retrying in %.1fs [image=%s]",
                    attempt + 1, MAX_DESCRIPTION_RETRIES, wait, image_path,
                )
                time.sleep(wait)
            else:
                raise

    # All retries exhausted
    runtime = settings.description_runtime_info()
    logger.error(
        "Scene description fallback [reason=retries_exhausted provider=%s model=%s image=%s]: %s",
        runtime["provider"], runtime["model"], image_path, last_exc,
    )
    return _describe_fallback(language)


def _describe_with_model(
    image_path: str,
    language: str,
) -> str:
    """
    Description via an external multimodal service.

    The service sees the image, reads the text, and understands the context.
    A separate OCR step is not needed — the description is built in a single request.

    Uses the connected SDK of the description provider.
    """
    runtime = settings.description_runtime_info()
    try:
        from PIL import Image

        client = _get_description_client()

        img = Image.open(image_path)

        prompt = _build_description_prompt(language)
        response = client.models.generate_content(
            model=settings.description_model,
            contents=[img, prompt],
            config=_build_description_generation_config(),
        )

        # response.text can be None (safety filter, empty response)
        if response.text is None:
            logger.warning(
                "Scene description fallback [reason=empty_response provider=%s model=%s project=%s location=%s auth=%s image=%s]",
                runtime["provider"],
                runtime["model"],
                runtime["project"],
                runtime["location"],
                runtime["auth_mode"],
                image_path,
            )
            return _describe_fallback(language)

        description = response.text.strip()

        # Trim if too long
        if len(description) > settings.max_description_length:
            description = description[: settings.max_description_length - 3] + "..."

        logger.info(
            "Scene description generated [provider=%s model=%s location=%s image=%s chars=%s]",
            runtime["provider"],
            runtime["model"],
            runtime["location"],
            image_path,
            len(description),
        )
        logger.debug(f"Scene description: '{description}'")
        return description

    except ImportError:
        logger.warning(
            "Scene description fallback [reason=sdk_missing provider=%s model=%s project=%s location=%s image=%s]",
            runtime["provider"],
            runtime["model"],
            runtime["project"],
            runtime["location"],
            image_path,
        )
        return _describe_fallback(language)
    except Exception as e:
        error_class, status_code = _classify_model_error(e)
        logger.error(
            "Scene description fallback [reason=%s status_code=%s provider=%s model=%s project=%s location=%s auth=%s image=%s]: %s",
            error_class,
            status_code,
            runtime["provider"],
            runtime["model"],
            runtime["project"],
            runtime["location"],
            runtime["auth_mode"],
            image_path,
            e,
        )
        return _describe_fallback(language)


def _classify_model_error(exc: Exception) -> tuple[str, int | None]:
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    message = f"{type(exc).__name__}: {exc}".lower()

    if status_code == 429 or "429" in message or "rate limit" in message or "too many requests" in message:
        return "rate_limit", status_code
    if status_code == 404 or "not found" in message or "does not have access to it" in message:
        return "model_not_found_or_not_enabled", status_code
    if status_code == 403 or "quota" in message or "resource exhausted" in message:
        return "quota_or_permission", status_code
    if status_code == 401 or "unauth" in message or "credential" in message:
        return "authentication", status_code
    if "timeout" in message or "deadline" in message:
        return "timeout", status_code
    return "api_error", status_code


def _describe_fallback(language: str) -> str:
    """
    Fallback without API.

    Without an external service, it is impossible to describe the frame meaningfully.
    Returns a generic description.
    """
    if language == "ru":
        return "На экране отображается новый визуальный элемент."
    return "A new visual element is displayed on screen."


def _build_description_prompt(language: str) -> str:
    """Build the multimodal prompt for scene descriptions."""
    lang_instruction = {
        "en": "Respond in English.",
        "ru": "Отвечай на русском языке.",
    }.get(language, "Respond in English.")

    return f"""You are an audio description assistant for visually impaired students watching educational videos.
Describe this frame so a blind person understands what is on screen.

Your description must:
1. Lead with the most important visual change first.
2. Quote all visible text exactly when it matters for comprehension (slide titles, bullet points, labels, captions).
3. Explain what is being demonstrated visually (body position, diagram layout, graph trends).
4. Mention important visual annotations (arrows, highlights, colored markers, warning symbols).
5. Sound natural to hear out loud as short audio description, with smooth phrasing and concrete nouns/verbs.
6. NEVER use generic phrases like "A new visual element", "The screen displays content", or "On-screen graphics".
7. If the frame looks nearly identical to a typical talking-head shot, describe the person's expression, gesture, clothing, or background instead — never repeat a generic description.

Avoid vague filler, broad generic statements, and repeated openings such as "This frame shows" or "The image shows".
Write 2-4 clear sentences, up to {settings.max_description_length} characters.
{lang_instruction}
"""


def _build_description_generation_config() -> dict:
    """Return explicit generation controls for scene descriptions."""
    return {
        "temperature": 0.2,
        "top_p": 0.8,
        # Multimodal descriptions need extra headroom to avoid truncation after
        # OCR-like text quoting and brief reasoning over the frame layout.
        "max_output_tokens": 512,
    }
