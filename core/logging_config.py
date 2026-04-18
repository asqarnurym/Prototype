"""Centralized logging setup for CLI, API, and tests."""

import logging
import sys
from logging.handlers import RotatingFileHandler

from core.config import settings

_logging_initialized = False


def setup_logging(level=logging.INFO, force=False):
    """Configure the root logger for the pipeline.

    Logs are written to stdout and to a rotating file under ``logs/``.

    Args:
        level: Logging level to apply to the handlers.
        force: Reinitialize logging even if it was already configured.

    Returns:
        The root logger instance.
    """
    global _logging_initialized

    # Guard against multiple initialization (embedded usage, tests)
    if _logging_initialized and not force:
        return logging.getLogger()

    log_dir = settings.project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "prototype.log"

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    file_handler = RotatingFileHandler(
        filename=log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root_logger = logging.getLogger()

    # Only add our handlers; keep host-application handlers intact.
    existing_names = {getattr(h, "name", None) for h in root_logger.handlers}

    if "prototype_console" not in existing_names:
        console_handler.name = "prototype_console"
        root_logger.addHandler(console_handler)

    if "prototype_file" not in existing_names:
        file_handler.name = "prototype_file"
        root_logger.addHandler(file_handler)

    root_logger.setLevel(min(root_logger.level or level, level))

    # Keep third-party libraries quieter than our own application logs.
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)

    _logging_initialized = True
    return root_logger
