"""
scene_indexer.py — Фильтрация визуальных событий и построение scene_index.json.

Принимает сырые события от PySceneDetect, фильтрует неинформативные,
генерирует описания через Gemini, и сохраняет индекс для on-demand доступа.

Индекс НЕ включает TTS-аудио — оно генерируется lazy по запросу пользователя.

Фильтрация:
- Минимальный интервал между сценами (settings.min_scene_interval_sec)
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.config import settings
from pipeline.visual.descriptor import generate_description

logger = logging.getLogger(__name__)


def build_scene_index(
    raw_events: list[dict],
    language: str = "en",
    output_path: str | None = None,
) -> list[dict]:
    """
    Фильтрует сырые visual events и строит индекс сцен с описаниями (ПАРАЛЛЕЛЬНО).
    """
    if not raw_events:
        logger.info("Нет визуальных событий для индексации.")
        if output_path:
            _save_index([], output_path)
        return []

    # 1. Сортировка и фильтрация
    sorted_events = sorted(raw_events, key=lambda e: e["event_time"])
    filtered = _filter_by_interval(sorted_events, settings.min_scene_interval_sec)
    runtime = settings.description_runtime_info()

    logger.info(
        "Scene indexing: %s raw events -> %s filtered. provider=%s model=%s project=%s location=%s workers=%s",
        len(sorted_events),
        len(filtered),
        runtime["provider"],
        runtime["model"],
        runtime["project"],
        runtime["location"],
        5,
    )

    # 2. Параллельная генерация описаний через Gemini
    def process_single_scene(index_tuple):
        i, event = index_tuple
        frame_path = event["frame_path"]
        # Добавляем простую логику повторных попыток для Gemini API (до 3 попыток с задержкой)
        for attempt in range(3):
            try:
                description = generate_description(frame_path, language)
                return {
                    "scene_id": i,
                    "time": event["event_time"],
                    "frame_path": str(frame_path),
                    "description": description,
                    "tts_cached": False,
                    "tts_path": None,
                }
            except Exception as e:
                if attempt < 2:
                    sleep_time = 2**attempt
                    logger.warning(
                        f"Ошибка Gemini на сцене {i} (попытка {attempt + 1}/3), ждем {sleep_time}с: {e}"
                    )
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Ошибка Gemini на сцене {i} (исчерпаны попытки): {e}")
                    return None

    scene_index = []
    # Используем 5 потоков для API (баланс между скоростью и rate limits)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_single_scene, enumerate(filtered)))

    # Отсеиваем неудачные запросы и восстанавливаем порядок
    scene_index = [r for r in results if r is not None]
    scene_index.sort(key=lambda s: s["time"])

    # Переприсваиваем ID после фильтрации ошибок (опционально)
    for i, s in enumerate(scene_index):
        s["scene_id"] = i

    logger.info(f"Scene index построен: {len(scene_index)} сцен")

    if output_path:
        _save_index(scene_index, output_path)

    return scene_index


def build_timeline_visual_events(scene_index: list[dict]) -> list[dict]:
    """
    Преобразует scene_index в публичный формат visual_events для timeline.json.

    timeline.json хранит только данные, нужные потребителям таймлайна:
    - event_time: время события в исходном видео
    - type: тип визуального события
    - description_text: текстовое описание сцены
    """
    visual_events = []
    for scene in scene_index:
        visual_events.append(
            {
                "event_time": scene["time"],
                "type": "scene_change",
                "description_text": scene["description"],
            }
        )
    return visual_events


def find_nearest_scene(
    scene_index: list[dict],
    current_time: float,
    tolerance_sec: float = 30.0,
) -> dict | None:
    """
    Находит ближайшую сцену к текущему времени видео.

    Используется при on-demand запросе: пользователь нажимает кнопку,
    система ищет ближайшую проиндексированную сцену.

    Args:
        scene_index: Список сцен из build_scene_index().
        current_time: Текущее время видео (секунды).
        tolerance_sec: Максимальное отклонение (сек). Если ближайшая сцена
                       дальше — возвращаем None.

    Returns:
        Ближайшая сцена или None.
    """
    if not scene_index:
        return None

    best = None
    best_distance = float("inf")

    for scene in scene_index:
        distance = abs(scene["time"] - current_time)
        if distance < best_distance:
            best_distance = distance
            best = scene

    if best_distance > tolerance_sec:
        return None

    return best


def load_scene_index(path: str) -> list[dict]:
    """Загружает scene_index.json с диска."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _filter_by_interval(
    events: list[dict],
    min_interval: float,
) -> list[dict]:
    """
    Отбрасывает события, слишком близкие по времени к предыдущему.

    Первое событие всегда проходит. Каждое следующее проходит только
    если прошло >= min_interval секунд с последнего принятого.
    """
    if not events:
        return []

    filtered = [events[0]]
    last_accepted_time = events[0]["event_time"]

    for event in events[1:]:
        if event["event_time"] - last_accepted_time >= min_interval:
            filtered.append(event)
            last_accepted_time = event["event_time"]

    return filtered


def _save_index(scene_index: list[dict], output_path: str) -> None:
    """Сохраняет scene index в JSON файл."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Не сохраняем frame_path — он привязан к temp-директории
    # Сохраняем только публичные поля
    export_data = []
    for scene in scene_index:
        export_data.append(
            {
                "scene_id": scene["scene_id"],
                "time": scene["time"],
                "description": scene["description"],
                "tts_cached": scene["tts_cached"],
            }
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Scene index сохранён: {output_path}")
