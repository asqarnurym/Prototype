"""
aligner.py — Фонемный alignment (привязка фонем к времени).

Опциональный модуль. Использует Montreal Forced Aligner (MFA) для
уточнения таймкодов до уровня отдельных фонем.

ВНИМАНИЕ: MFA на Windows часто конфликтует по зависимостям.
По умолчанию этот модуль ОТКЛЮЧЁН (settings.use_mfa = False).
Если MFA недоступен, используем word-level таймкоды из faster-whisper
как основной источник timing-информации. Для MVP этого достаточно.
"""

import logging
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)


def align_phonemes(
    audio_path: str,
    transcript_data: dict[str, Any],
    language: str = "en",
) -> list[dict]:
    """
    Уточняет temporal alignment до уровня фонем.

    Если MFA включён (settings.use_mfa = True) — использует MFA.
    Если нет — возвращает пустой список фонем (word-level достаточен для MVP).

    Args:
        audio_path: Путь к WAV-файлу.
        transcript_data: Результат работы transcriber.transcribe().
        language: Код языка ("en", "ru").

    Returns:
        Список фонем с таймкодами:
        [{"phoneme": "HH", "start": 0.0, "end": 0.05, "word": "Hello"}, ...]
        Или пустой список, если MFA отключён.
    """
    if not settings.use_mfa:
        logger.info(
            "MFA отключён (settings.use_mfa = False). "
            "Используем word-level alignment из faster-whisper."
        )
        return []

    # ── MFA alignment (опционально) ──────────────────────────────
    # Этот блок выполняется только если MFA установлен и включён.
    try:
        return _run_mfa_alignment(audio_path, transcript_data, language)
    except Exception as e:
        logger.warning(f"MFA alignment не удался: {e}. Fallback на word-level alignment.")
        return []


def _run_mfa_alignment(
    audio_path: str,
    transcript_data: dict[str, Any],
    language: str,
) -> list[dict]:
    """
    Запускает MFA для получения фонемного alignment.

    MFA работает так:
    1) На вход: WAV + текст транскрипта + языковая модель
    2) На выход: TextGrid файл с точными таймкодами для каждой фонемы

    Этот метод является заглушкой для MVP.
    Полная реализация MFA потребует:
    - Установки MFA через conda: `conda install -c conda-forge montreal-forced-aligner`
    - Скачивания acoustic model: `mfa model download acoustic english_mfa`
    - Скачивания словаря: `mfa model download dictionary english_mfa`
    """
    logger.warning(
        "MFA integration is a placeholder. Full MFA support will be added post-MVP if needed."
    )

    # TODO: Полная реализация MFA alignment
    # Шаги для реализации:
    # 1. Подготовить текстовый файл .lab с тексом транскрипта
    # 2. Запустить `mfa align <corpus_dir> <dict> <model> <output_dir>`
    # 3. Прочитать TextGrid файл и извлечь фонемы с таймкодами
    # 4. Преобразовать в формат [{"phoneme": ..., "start": ..., "end": ...}]

    return []
