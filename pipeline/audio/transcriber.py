"""
transcriber.py — Распознавание речи (ASR) с временными метками слов.

[DATA FLOW]
ВХОД: Путь к локальному аудиофайлу (.wav) и код языка ("en", "ru").
ВЫХОД: Словарь словарей (Транскрипт):
  - "language": str
  - "segments": list of dict (предложения)
  - "words": list of dict (отдельные слова с временными метками).
ОТПРАВЛЯЕТСЯ В: main.py и API-слой для экспорта таймлайна и субтитров.

Использует faster-whisper для транскрипции аудио.
"""

import logging
import threading
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from core.config import settings

logger = logging.getLogger(__name__)

# ── Глобальный кэш модели ───────────────────────────────────────
# Модель тяжёлая (~1.5GB для medium), загружаем один раз и переиспользуем.
_model: WhisperModel | None = None
_model_lock = threading.Lock()


def _get_model() -> WhisperModel:
    """
    Загружает и кэширует модель faster-whisper.
    При первом вызове модель скачивается из HuggingFace (если не в кэше).
    """
    global _model
    if _model is None:
        with _model_lock:
            # Double-checked locking для потокобезопасности
            if _model is None:
                logger.info(
                    f"Загрузка модели faster-whisper: "
                    f"size={settings.whisper_model_size}, "
                    f"device={settings.whisper_device}, "
                    f"compute_type={settings.whisper_compute_type}"
                )
                _model = WhisperModel(
                    settings.whisper_model_size,
                    device=settings.whisper_device,
                    compute_type=settings.whisper_compute_type,
                )
                logger.info("Модель faster-whisper загружена успешно")
    return _model


def transcribe(audio_path: str, language: str | None = None) -> dict[str, Any]:
    """
    Распознаёт речь и возвращает транскрипт с временными метками.

    Args:
        audio_path: Путь к WAV-файлу (16kHz mono).
        language: Код языка ("en", "ru"). None — автодетекция.

    Returns:
        Словарь с ключами:
        - "language": str — определённый язык
        - "segments": list — список сегментов с текстом и временем
        - "words": list — список слов с точными временными метками

    Пример выхода:
        {
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 4.5, "text": "Hello and welcome..."}
            ],
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.98},
                {"word": "and", "start": 0.5, "end": 0.7, "probability": 0.95},
            ]
        }
    """
    audio = Path(audio_path)
    if not audio.exists():
        raise FileNotFoundError(f"Аудиофайл не найден: {audio_path}")

    model = _get_model()

    logger.info(f"Начинаем транскрипцию: {audio_path} (язык: {language or 'auto'})")

    # ── Запуск транскрипции ───────────────────────────────────────
    # word_timestamps=True — включает определение времени для каждого слова.
    # Это ключевая функция для создания точных субтитров.
    segments_iter, info = model.transcribe(
        str(audio),
        language=language,
        word_timestamps=True,
        beam_size=5,  # Качество поиска (5 — хороший баланс)
        vad_filter=True,  # Фильтрация тишины через VAD
        vad_parameters=dict(
            min_silence_duration_ms=500,  # Минимум 500мс тишины для разделения
        ),
    )

    detected_language = info.language
    logger.info(
        f"Язык определён: {detected_language} (вероятность: {info.language_probability:.2%})"
    )

    # ── Сбор результатов ─────────────────────────────────────────
    # Итератор faster-whisper ленивый — нужно материализовать в список.
    segments_list = []
    words_list = []

    for segment in segments_iter:
        # Сохраняем сегмент (обычно одно предложение)
        seg_data = {
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": segment.text.strip(),
        }
        segments_list.append(seg_data)

        # Сохраняем каждое слово с индивидуальными таймкодами
        if segment.words:
            for word in segment.words:
                words_list.append(
                    {
                        "word": word.word.strip(),
                        "start": round(word.start, 3),
                        "end": round(word.end, 3),
                        "probability": round(word.probability, 4),
                    }
                )

    logger.info(f"Транскрипция завершена: {len(segments_list)} сегментов, {len(words_list)} слов")

    return {
        "language": detected_language,
        "segments": segments_list,
        "words": words_list,
    }
