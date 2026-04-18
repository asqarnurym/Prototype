"""
scene_detect.py — Детекция ключевых кадров (смен сцен) в видео.

[DATA FLOW]
ВХОД: Путь к локальному видеофайлу (.mp4).
ВЫХОД: Список dict (Visual Events). Каждый dict:
  - "event_time": секунды (float)
  - "frame_path": путь к PNG кадру
  - "scene_index": индекс (int)
ОТПРАВЛЯЕТСЯ В: pipeline/visual/scene_indexer.py (для фильтрации и описания).

Использует PySceneDetect для извлечения png кадров.
"""

import logging
from pathlib import Path

import cv2
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector

from core.config import settings

logger = logging.getLogger(__name__)


def detect_scenes(video_path: str, output_dir: str | None = None) -> list[dict]:
    """
    Находит границы сцен в видео и извлекает ключевые кадры.

    Для учебных видео (лекции, презентации) "сцена" — это, как правило,
    смена слайда, появление нового графика или диаграммы.

    Args:
        video_path: Путь к исходному видеофайлу.
        output_dir: Папка для сохранения кадров. None → settings.temp_dir/frames.

    Returns:
        Список визуальных событий:
        [
            {
                "event_time": 10.5,        # Время начала сцены (сек)
                "frame_path": "path.png",  # Путь к извлечённому кадру
                "scene_index": 0,          # Индекс сцены
            },
            ...
        ]
    """
    video = Path(video_path)
    if not video.exists():
        raise FileNotFoundError(f"Видеофайл не найден: {video_path}")

    # Папка для сохранения извлечённых кадров
    frames_dir = Path(output_dir) if output_dir else settings.temp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Детекция сцен: {video_path} (threshold={settings.scene_threshold})")

    # ── Настройка PySceneDetect ──────────────────────────────────
    video_stream = open_video(str(video))
    scene_manager = SceneManager()

    # ContentDetector — основной детектор для учебного контента.
    # threshold: чувствительность к изменениям (27 — хорошо для презентаций).
    # min_scene_len: минимальная длительность сцены (избегаем ложных срабатываний).
    scene_manager.add_detector(
        ContentDetector(
            threshold=settings.scene_threshold,
            min_scene_len=int(settings.min_scene_length_sec * video_stream.frame_rate),
        )
    )

    # ── Анализ видео ─────────────────────────────────────────────
    scene_manager.detect_scenes(video_stream)
    scene_list = scene_manager.get_scene_list()

    logger.info(f"Обнаружено {len(scene_list)} сцен")

    # Fallback для Screencast-видео (если сцен < 3, используем Uniform Sampling каждые 30 секунд)
    if len(scene_list) < 3:
        logger.warning(
            f"Найдено слишком мало сцен ({len(scene_list)}). Возможен Screencast. Включаем Uniform Sampling (30s)."
        )

        # Сохраняем реально обнаруженные сцены
        original_scenes = list(scene_list)
        original_times = {s[0].get_seconds() for s in original_scenes}

        # Получаем реальную длительность из cv2
        cap = cv2.VideoCapture(str(video))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = frame_count / fps if fps > 0 else 0
        cap.release()

        # Генерируем искусственные сцены каждые 30 секунд
        class FakeTimecode:
            def __init__(self, sec):
                self.sec = sec

            def get_seconds(self):
                return self.sec

        interval = 30.0
        current = 0.0
        uniform_scenes = []

        while current < duration_sec:
            # Не добавляем uniform sample если рядом уже есть реальная сцена
            too_close = any(
                abs(current - t) < settings.min_scene_interval_sec for t in original_times
            )
            if not too_close:
                start_tc = FakeTimecode(current)
                end_tc = FakeTimecode(min(current + interval, duration_sec))
                uniform_scenes.append((start_tc, end_tc))
            current += interval

        # Объединяем реальные и искусственные сцены
        scene_list = original_scenes + uniform_scenes
        scene_list.sort(key=lambda s: s[0].get_seconds())

        logger.info(
            f"Сгенерировано {len(uniform_scenes)} искусственных сцен (Uniform Sampling). "
            f"Итого с оригинальными: {len(scene_list)}."
        )

    # ── Извлечение ключевых кадров ───────────────────────────────
    # Для каждой сцены берём первый кадр (начало сцены) — это момент,
    # когда произошло визуальное изменение (новый слайд, график и т.д.).
    visual_events = []
    cap = cv2.VideoCapture(str(video))
    try:
        for idx, (start_time, _end_time) in enumerate(scene_list):
            # Время начала сцены в секундах
            event_time = start_time.get_seconds()

            # Позиционируемся на нужный кадр
            cap.set(cv2.CAP_PROP_POS_MSEC, event_time * 1000)
            success, frame = cap.read()

            if not success:
                logger.warning(f"Не удалось извлечь кадр для сцены {idx} @ {event_time:.2f}s")
                continue

            # Сохраняем кадр как PNG
            frame_filename = f"scene_{idx:04d}_{event_time:.2f}s.png"
            frame_path = frames_dir / frame_filename
            cv2.imwrite(str(frame_path), frame)

            visual_events.append(
                {
                    "event_time": round(event_time, 3),
                    "frame_path": str(frame_path),
                    "scene_index": idx,
                }
            )

            logger.debug(f"Кадр {idx}: {event_time:.2f}s → {frame_path}")
    finally:
        cap.release()

    logger.info(f"Извлечено {len(visual_events)} ключевых кадров")
    return visual_events
