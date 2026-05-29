"""Validate the local runtime against the project's pinned environment."""

from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


EXPECTED_PYTHON = (3, 12, 10)

RUNTIME_IMPORTS: list[tuple[str, str]] = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic-settings", "pydantic_settings"),
    ("python-dotenv", "dotenv"),
    ("faster-whisper", "faster_whisper"),
    ("Pillow", "PIL"),
    ("scenedetect", "scenedetect"),
    ("opencv-python", "cv2"),
    ("google-genai", "google.genai"),
    ("google-cloud-texttospeech", "google.cloud.texttospeech"),
    ("edge-tts", "edge_tts"),
]

DEV_IMPORTS: list[tuple[str, str]] = [
    ("datasets", "datasets"),
    ("langdetect", "langdetect"),
    ("yt-dlp", "yt_dlp"),
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("seaborn", "seaborn"),
    ("pytest", "pytest"),
]


def _status(ok: bool, label: str, details: str = "") -> bool:
    prefix = "PASS" if ok else "FAIL"
    print(f"[{prefix}] {label}")
    if details:
        print(f"       {details}")
    return ok


def _warn(label: str, details: str = "") -> None:
    print(f"[WARN] {label}")
    if details:
        print(f"       {details}")


def _check_python() -> bool:
    version = sys.version_info[:3]
    return _status(
        version == EXPECTED_PYTHON,
        "Python version",
        f"expected {'.'.join(map(str, EXPECTED_PYTHON))}, got {'.'.join(map(str, version))}",
    )


def _check_venv(allow_system_python: bool) -> bool:
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        return _status(True, "Virtual environment", sys.prefix)
    if allow_system_python:
        _warn(
            "Virtual environment", "running on system Python because --allow-system-python was used"
        )
        return True
    return _status(False, "Virtual environment", "activate .venv or use scripts/bootstrap.ps1")


def _check_env_template(project_root: Path) -> bool:
    template = project_root / ".env.example"
    return _status(template.exists(), ".env.example", str(template))


def _load_runtime_settings(project_root: Path) -> Settings:
    from core.config import Settings

    env_file = project_root / ".env"
    return Settings(_env_file=env_file if env_file.exists() else None, project_root=project_root)


def _check_google_credentials(settings: Settings) -> bool:
    creds = settings.google_application_credentials
    if not creds:
        _warn(
            "GOOGLE_APPLICATION_CREDENTIALS",
            f"not set; active TTS provider is {settings.tts_provider}",
        )
        return True
    path = Path(creds)
    return _status(
        path.exists(),
        "GOOGLE_APPLICATION_CREDENTIALS",
        f"{path} (active TTS provider: {settings.tts_provider})",
    )


def _check_description_service_settings(settings: Settings) -> bool:
    if settings.description_mode == "developer":
        return _status(
            True,
            "Gemini Developer API",
            "GEMINI_API_KEY is configured; Vertex AI project settings are optional",
        )
    if settings.description_mode == "vertex":
        return _status(
            True,
            "Vertex AI Gemini",
            f"project={settings.google_cloud_project}, location={settings.google_cloud_location}",
        )
    if not settings.description_service_configured:
        _warn(
            "Gemini descriptions",
            "Neither GEMINI_API_KEY nor GOOGLE_CLOUD_PROJECT is set; summaries and scene descriptions will use fallback mode",
        )
        return True
    return True


def _import_module(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except Exception:
        return False


def _check_imports(profile: str) -> bool:
    ok = True
    imports = list(RUNTIME_IMPORTS)
    if profile == "dev":
        imports.extend(DEV_IMPORTS)
    for package_name, import_name in imports:
        ok = _status(_import_module(import_name), f"Import {package_name}", import_name) and ok
    return ok


def _resolve_ffmpeg_commands(settings: Settings) -> tuple[str, str]:
    return settings.ffmpeg_path, settings.ffprobe_path


def _check_command(command: str) -> bool:
    exe = shutil.which(command)
    if exe is None and Path(command).exists():
        exe = command
    if exe is None:
        return _status(False, f"Command {command}", "not found on PATH")
    try:
        subprocess.run([exe, "-version"], capture_output=True, text=True, check=True)
        return _status(True, f"Command {Path(command).name}", exe)
    except Exception as exc:
        return _status(False, f"Command {Path(command).name}", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("runtime", "dev"), default="runtime")
    parser.add_argument("--allow-system-python", action="store_true")
    args = parser.parse_args()

    project_root = PROJECT_ROOT
    settings = _load_runtime_settings(project_root)
    ok = True

    ok = _check_python() and ok
    ok = _check_venv(args.allow_system_python) and ok
    ok = _check_env_template(project_root) and ok
    ok = _check_imports(args.profile) and ok

    ffmpeg_cmd, ffprobe_cmd = _resolve_ffmpeg_commands(settings)
    ok = _check_command(ffmpeg_cmd) and ok
    ok = _check_command(ffprobe_cmd) and ok
    ok = _check_google_credentials(settings) and ok
    ok = _check_description_service_settings(settings) and ok

    if ok:
        print("[PASS] Environment verification completed successfully.")
        return 0
    print("[FAIL] Environment verification failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
