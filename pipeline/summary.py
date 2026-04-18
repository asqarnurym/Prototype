"""
summary.py — Генерация краткой сводки и chapter markers через Gemini.

Для ADHD/дислексия пользователей:
- summary_points: 3-5 ключевых тезисов видео
- chapters: 3-7 логических разделов с таймкодами

Используется и в CLI pipeline (main.py), и в API (server.py).
Результат кэшируется в summary.json.
"""

import json
import logging
import re
import threading
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)
SUMMARY_CACHE_VERSION = 3


_client = None
_client_lock = threading.Lock()


def _get_gemini_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                from google import genai
                from google.genai import types

                runtime = settings.description_runtime_info()
                logger.info(
                    "Initializing Gemini Vertex client for summaries [sdk=%s model=%s project=%s location=%s auth=%s service_account=%s]",
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


def generate_summary(
    scenes: list[dict],
    job_id: str,
    language: str = "en",
    output_path: str | None = None,
    transcript_segments: list[str] | None = None,
) -> dict:
    """
    Генерирует сводку видео на основе описаний сцен.

    Args:
        scenes: Список сцен из scene_index.json (каждая с 'time' и 'description').
        job_id: Идентификатор job (для результата).
        language: Язык ('en' или 'ru').
        output_path: Путь для сохранения summary.json. None = не сохранять.

    Returns:
        Словарь с summary_points и chapters.
    """
    runtime = settings.description_runtime_info()
    if not scenes:
        result = {
            "job_id": job_id,
            "language": language,
            "summary_version": SUMMARY_CACHE_VERSION,
            "summary_points": [],
            "chapters": [],
        }
        if output_path:
            _save(result, output_path)
        return result

    # Без Vertex AI конфигурации — fallback
    if not settings.description_service_configured:
        logger.warning(
            "Summary fallback [reason=not_configured provider=%s model=%s project=%s location=%s auth=%s job_id=%s]",
            runtime["provider"],
            runtime["model"],
            runtime["project"],
            runtime["location"],
            runtime["auth_mode"],
            job_id,
        )
        return _fallback_from_scenes(
            scenes,
            job_id,
            language,
            output_path,
            transcript_segments=transcript_segments,
            reason=(
                "Summary uses scene descriptions because the external summarization model "
                "is not configured."
            ),
        )

    try:
        client = _get_gemini_client()

        scene_descriptions = "\n".join(f"[{s['time']:.0f}s] {s['description']}" for s in scenes)
        transcript_context = _build_transcript_context(transcript_segments)

        if language == "ru":
            prompt = f"""Ты — образовательный ассистент, помогающий студентам с СДВГ и дислексией.
На основе описаний сцен из учебного видео, создай:

1. ПОДРОБНУЮ СВОДКУ (5-8 пунктов) содержания, ключевых тем и важных действий видео. Пиши на русском языке.
2. ГЛАВЫ — раздели видео на 3-7 логических глав с таймкодами и короткими названиями. Пиши на русском языке.

Описания сцен:
{scene_descriptions}

Краткие фрагменты речи/субтитров:
{transcript_context}

Ответь СТРОГО в формате JSON (без markdown, без code blocks):
{{
  "summary_points": ["пункт 1", "пункт 2", "пункт 3"],
  "chapters": [
    {{"time": 0.0, "title": "Введение"}},
    {{"time": 60.0, "title": "Основная тема"}}
  ]
}}

ВАЖНО: Весь текст в summary_points и chapters.title должен быть на русском языке.
"""
        else:
            prompt = f"""You are an educational assistant helping students with ADHD and dyslexia.
Based on the following scene descriptions from an educational video, generate:

1. A useful SUMMARY (5-8 bullet points) of the video's content, key topics, and important actions.
2. CHAPTERS — divide the video into 3-7 logical chapters with timestamps and short titles.

Scene descriptions:
{scene_descriptions}

Short transcript or subtitle excerpts:
{transcript_context}

Format your response EXACTLY as JSON (no markdown, no code blocks):
{{
  "summary_points": ["point 1", "point 2", "point 3"],
  "chapters": [
    {{"time": 0.0, "title": "Introduction"}},
    {{"time": 60.0, "title": "Main Topic"}}
  ]
}}
"""

        logger.info(
            "Generating summary via Gemini [provider=%s model=%s project=%s location=%s auth=%s job_id=%s scenes=%s]",
            runtime["provider"],
            runtime["model"],
            runtime["project"],
            runtime["location"],
            runtime["auth_mode"],
            job_id,
            len(scenes),
        )
        response = client.models.generate_content(
            model=settings.description_model,
            contents=[prompt],
        )

        if response.text is None:
            logger.warning(
                "Summary fallback [reason=empty_response provider=%s model=%s project=%s location=%s auth=%s job_id=%s]",
                runtime["provider"],
                runtime["model"],
                runtime["project"],
                runtime["location"],
                runtime["auth_mode"],
                job_id,
            )
            raise ValueError("Gemini returned empty response")

        # Робастный парсинг JSON из ответа Gemini
        response_text = response.text.strip()

        # Убираем markdown code block(s) — ```json ... ``` или ``` ... ```
        code_block = re.search(r"```(?:json)?\s*\n(.*?)```", response_text, re.DOTALL)
        if code_block:
            response_text = code_block.group(1).strip()
        elif response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]).strip()

        # Ищем JSON объект в тексте (от первой до последней скобки)
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            response_text = response_text[start_idx : end_idx + 1]

        parsed = json.loads(response_text)
        summary_points = _enrich_summary_points(
            parsed.get("summary_points", []),
            scenes,
            transcript_segments,
        )

        result = {
            "job_id": job_id,
            "language": language,
            "summary_version": SUMMARY_CACHE_VERSION,
            "summary_points": summary_points,
            "chapters": parsed.get("chapters", []),
        }

        logger.info(
            "Summary generated [provider=%s model=%s location=%s job_id=%s points=%s chapters=%s]",
            runtime["provider"],
            runtime["model"],
            runtime["location"],
            job_id,
            len(result["summary_points"]),
            len(result["chapters"]),
        )

    except Exception as e:
        error_class, status_code = _classify_model_error(e)
        logger.error(
            "Summary fallback [reason=%s status_code=%s provider=%s model=%s project=%s location=%s auth=%s job_id=%s]: %s",
            error_class,
            status_code,
            runtime["provider"],
            runtime["model"],
            runtime["project"],
            runtime["location"],
            runtime["auth_mode"],
            job_id,
            e,
        )
        return _fallback_from_scenes(
            scenes,
            job_id,
            language,
            output_path,
            transcript_segments=transcript_segments,
            reason="Summary generation failed. Chapters are auto-generated from scene descriptions.",
        )

    if output_path:
        _save(result, output_path)

    return result


def _fallback_from_scenes(
    scenes: list[dict],
    job_id: str,
    language: str,
    output_path: str | None,
    transcript_segments: list[str] | None,
    reason: str,
) -> dict:
    """Create useful summary points and chapter markers directly from scenes."""
    chapters = []
    last_time = -30
    for s in scenes:
        if s["time"] - last_time >= 30:
            chapters.append(
                {
                    "time": s["time"],
                    "title": s["description"][:80],
                }
            )
            last_time = s["time"]

    result = {
        "job_id": job_id,
        "language": language,
        "summary_version": SUMMARY_CACHE_VERSION,
        "summary_points": _build_summary_points_from_scenes(scenes, transcript_segments),
        "chapters": chapters,
    }

    if output_path:
        _save(result, output_path)

    return result


def _save(result: dict, output_path: str) -> None:
    """Сохраняет summary.json."""
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Summary cached: {output_path}")


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
    if "empty response" in message:
        return "empty_response", status_code
    return "api_error", status_code


def _build_summary_points_from_scenes(
    scenes: list[dict],
    transcript_segments: list[str] | None,
) -> list[str]:
    """Build richer summary bullets from scenes and transcript snippets."""
    points: list[str] = []
    seen: set[str] = set()

    for scene in scenes:
        description = str(scene.get("description", "")).strip()
        if not description:
            continue

        normalized = description.rstrip(". ")
        key = normalized.lower()
        if key in seen:
            continue

        seen.add(key)
        points.append(normalized + ".")
        if len(points) == 5:
            break

    for snippet in _clean_transcript_segments(transcript_segments):
        if len(points) >= 6:
            break
        normalized = snippet.rstrip(". ")
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        points.append(f"Spoken content highlights: {normalized}.")

    return points


def _enrich_summary_points(
    generated_points: list[str],
    scenes: list[dict],
    transcript_segments: list[str] | None,
) -> list[str]:
    """Keep model output, but supplement underfilled summaries from local context."""
    points: list[str] = []
    seen: set[str] = set()

    for point in generated_points:
        normalized = " ".join(str(point).split()).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        points.append(normalized)

    target_size = min(
        5, max(3, len(_build_summary_points_from_scenes(scenes, transcript_segments)))
    )
    if len(points) >= target_size:
        return points

    for fallback_point in _build_summary_points_from_scenes(scenes, transcript_segments):
        key = fallback_point.lower()
        if key in seen:
            continue
        seen.add(key)
        points.append(fallback_point)
        if len(points) >= target_size:
            break

    return points


def _build_transcript_context(transcript_segments: list[str] | None) -> str:
    snippets = _clean_transcript_segments(transcript_segments)
    if not snippets:
        return "No transcript excerpts available."
    return "\n".join(f"- {snippet}" for snippet in snippets[:8])


def _clean_transcript_segments(transcript_segments: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for snippet in transcript_segments or []:
        normalized = " ".join(str(snippet).split()).strip()
        if len(normalized) < 20:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized[:180])
        if len(cleaned) == 8:
            break
    return cleaned
