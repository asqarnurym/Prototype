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

from core.config import settings

logger = logging.getLogger(__name__)


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
    runtime = settings.description_runtime_info()
    if settings.description_service_configured:
        return _describe_with_model(image_path, language)

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
