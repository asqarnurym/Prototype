"""
json_export.py — Экспорт полного таймлайна в формате JSON.

timeline.json — это главный структурированный артефакт системы.
Он содержит всю информацию о видео:
- segments: сегменты речи (предложения) с таймкодами
- words: отдельные слова с точными таймкодами
- phonemes: фонемы (если MFA включён)
 - visual_events: описанные визуальные события с таймкодами

Этот файл может использоваться:
- Фронтендом для интерактивного плеера
- Аналитикой для оценки качества субтитров
- Другими инструментами доступности
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def export_timeline_json(
    timeline: dict,
    output_path: str,
    pretty: bool = True,
) -> str:
    """
    Экспортирует полный таймлайн в JSON-файл.

    Args:
        timeline: Финальный таймлайн пайплайна.
        output_path: Путь для сохранения .json файла.
        pretty: Если True — формат с отступами (читаемый), False — компактный.

    Returns:
        Путь к сохранённому JSON-файлу.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # ── Формируем финальную структуру ────────────────────────────
    # Эта структура соответствует контракту из Prototype.md (раздел 7)
    output_data = {
        "language": timeline.get("language", "en"),
        "detected_language": timeline.get(
            "detected_language",
            timeline.get("language", "en"),
        ),
        "segments": timeline.get("segments", []),
        "words": timeline.get("words", []),
        "phonemes": timeline.get("phonemes", []),
        "visual_events": _clean_visual_events(timeline.get("visual_events", [])),
    }

    # ── Записываем JSON ──────────────────────────────────────────
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            output_data,
            f,
            ensure_ascii=False,  # Сохраняем кириллицу (RU)
            indent=2 if pretty else None,
        )

    logger.info(
        f"Timeline JSON сохранён: {output_path} "
        f"({len(output_data['segments'])} segments, "
        f"{len(output_data['words'])} words, "
        f"{len(output_data['visual_events'])} visual events)"
    )
    return output_path


def _clean_visual_events(events: list[dict]) -> list[dict]:
    """
    Очищает визуальные события для экспорта.

    Убирает внутренние поля (пути к файлам), оставляет только
    публичные данные, нужные потребителям таймлайна.
    """
    cleaned = []
    for event in events:
        if "event_time" not in event:
            raise ValueError(
                "visual_events must use the timeline schema with 'event_time'. "
                "Convert scene_index entries via build_timeline_visual_events() first."
            )
        if "description_text" not in event:
            raise ValueError(
                "visual_events must use the timeline schema with 'description_text'. "
                "Convert scene_index entries via build_timeline_visual_events() first."
            )

        cleaned.append(
            {
                "event_time": event["event_time"],
                "type": event.get("type", "scene_change"),
                "description_text": event["description_text"],
            }
        )
    return cleaned
