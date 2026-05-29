"""
core/config.py — Unified project configuration using pydantic-settings.
"""

import json
import logging
import os
from contextlib import suppress
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_LANGUAGES = ["en", "ru"]
DEFAULT_TTS_VOICES = {
    "en": {
        "google": "en-US-Neural2-D",
        "edge": "en-US-GuyNeural",
    },
    "ru": {
        "google": "ru-RU-Wavenet-B",
        "edge": "ru-RU-DmitryNeural",
    },
}


# CUDA auto-detection for faster-whisper
def _setup_nvidia_dll_paths():
    import site

    nvidia_dirs = []
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        nvidia_base = Path(sp) / "nvidia"
        if nvidia_base.is_dir():
            for sub in nvidia_base.iterdir():
                bin_dir = sub / "bin"
                if bin_dir.is_dir():
                    nvidia_dirs.append(str(bin_dir))
        ct2_dir = Path(sp) / "ctranslate2"
        if ct2_dir.is_dir():
            nvidia_dirs.append(str(ct2_dir))
    if not nvidia_dirs:
        return
    existing = os.environ.get("PATH", "")
    new_entries = [d for d in nvidia_dirs if d not in existing]
    if new_entries:
        os.environ["PATH"] = os.pathsep.join(new_entries) + os.pathsep + existing
    if hasattr(os, "add_dll_directory"):
        for d in nvidia_dirs:
            with suppress(OSError):
                os.add_dll_directory(d)


def _detect_device():
    try:
        _setup_nvidia_dll_paths()
    except Exception as e:
        logger.debug(f"Failed to set up nvidia DLL paths: {e}")
    try:
        import ctypes

        ctypes.cdll.LoadLibrary("cublas64_12.dll")
        return "cuda", "int8_float16"
    except OSError:
        return "cpu", "int8"


_device, _compute = _detect_device()


class Settings(BaseSettings):
    """
    Project configuration.
    Values can be overridden via .env file or environment variables.
    """

    # ── Paths ─────────────────────────────────────────────────────────
    project_root: Path = Field(default=PROJECT_ROOT)
    input_dir: Path = Field(default=PROJECT_ROOT / "input")
    output_dir: Path = Field(default=PROJECT_ROOT / "output")
    temp_dir: Path = Field(default=PROJECT_ROOT / "temp")

    # ── ASR settings (faster-whisper) ───────────────────────────────
    whisper_model_size: str = "medium"
    whisper_device: str = _device
    whisper_compute_type: str = _compute

    # ── Visual pipeline settings (PySceneDetect) ───────────────────
    scene_threshold: float = 27.0
    min_scene_length_sec: float = 2.0
    min_scene_interval_sec: float = 5.0
    # Note: MAX_SCENES_PER_VIDEO limit removed — adaptive density

    # ── Description service settings (Gemini via Vertex AI or Developer API) ────────────
    google_cloud_project: str = ""
    google_cloud_location: str = "global"
    gemini_api_key: str = ""
    description_model: str = Field(default="gemini-2.5-flash")
    max_description_length: int = 400

    # ── TTS settings ──────────────────────────────────────────────
    # Auto-detect: use Google TTS if valid credentials are configured, else edge-tts.
    # Explicit TTS_PROVIDER still overrides auto-detection.
    google_application_credentials: str = ""
    tts_provider: str | None = None
    tts_voices: dict[str, dict[str, str]] = Field(
        default_factory=lambda: {
            language: voices.copy() for language, voices in DEFAULT_TTS_VOICES.items()
        }
    )

    # ── Other tools ──────────────────────────────────────────────────
    use_mfa: bool = False
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    supported_languages: list[str] = Field(default_factory=lambda: SUPPORTED_LANGUAGES.copy())
    default_language: str = "en"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("google_application_credentials", mode="before")
    @classmethod
    def _normalize_google_credentials(cls, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value)

    @field_validator("google_cloud_project", "google_cloud_location", mode="before")
    @classmethod
    def _normalize_google_cloud_value(cls, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value)

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def _normalize_gemini_api_key(cls, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value)

    @field_validator("tts_provider", mode="before")
    @classmethod
    def _normalize_tts_provider(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized or None
        return value

    @field_validator("ffmpeg_path", mode="before")
    @classmethod
    def _normalize_ffmpeg_path(cls, value):
        if value is None:
            return "ffmpeg"
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or "ffmpeg"
        return str(value)

    @field_validator("ffprobe_path", mode="before")
    @classmethod
    def _normalize_ffprobe_path(cls, value):
        if value is None:
            return "ffprobe"
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or "ffprobe"
        return str(value)

    def _resolve_google_credentials_path(self) -> tuple[str, bool]:
        if not self.google_application_credentials:
            return "", False

        credentials_path = Path(self.google_application_credentials).expanduser()
        if not credentials_path.is_absolute():
            credentials_path = self.project_root / credentials_path

        normalized_path = str(credentials_path.resolve(strict=False))
        return normalized_path, credentials_path.exists()

    def _resolve_tool_path(self, tool_path: str, default_command: str) -> str:
        if not tool_path:
            return default_command

        candidate = Path(tool_path).expanduser()
        if candidate.is_absolute():
            return str(candidate.resolve(strict=False))

        if tool_path.startswith(".") or "/" in tool_path or "\\" in tool_path:
            return str((self.project_root / candidate).resolve(strict=False))

        return tool_path

    @model_validator(mode="after")
    def _finalize_runtime_defaults(self):
        if self.tts_provider not in (None, "edge", "google"):
            raise ValueError("TTS_PROVIDER must be 'edge' or 'google'.")

        credentials_path, credentials_exist = self._resolve_google_credentials_path()
        self.google_application_credentials = credentials_path

        if credentials_path and credentials_exist:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        elif credentials_path and self.tts_provider is None:
            logger.warning(
                "GOOGLE_APPLICATION_CREDENTIALS points to a missing file: %s. "
                "Auto-detect will use edge-tts.",
                credentials_path,
            )

        if self.tts_provider is None:
            self.tts_provider = "google" if credentials_exist else "edge"

        if self.google_cloud_project:
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.google_cloud_project
        if self.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self.gemini_api_key

        self.ffmpeg_path = self._resolve_tool_path(self.ffmpeg_path, "ffmpeg")
        self.ffprobe_path = self._resolve_tool_path(self.ffprobe_path, "ffprobe")

        return self

    @property
    def vertex_description_configured(self) -> bool:
        return bool(self.google_cloud_project and self.google_cloud_location)

    @property
    def gemini_developer_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def description_service_configured(self) -> bool:
        return self.description_mode != "fallback"

    @property
    def description_mode(self) -> str:
        if self.vertex_description_configured:
            return "vertex"
        if self.gemini_developer_configured:
            return "developer"
        return "fallback"

    def _service_account_info(self) -> dict[str, str | None]:
        creds_path = self.google_application_credentials
        if not creds_path:
            return {
                "auth_mode": "adc",
                "credentials_file": None,
                "service_account_email": None,
                "service_account_project": None,
            }

        path = Path(creds_path)
        info: dict[str, str | None] = {
            "auth_mode": "service_account_json",
            "credentials_file": path.name,
            "service_account_email": None,
            "service_account_project": None,
        }
        if not path.exists():
            return info

        with suppress(OSError, json.JSONDecodeError):
            payload = json.loads(path.read_text(encoding="utf-8"))
            info["service_account_email"] = payload.get("client_email")
            info["service_account_project"] = payload.get("project_id")
        return info

    def description_runtime_info(self) -> dict[str, str | bool | None]:
        mode = self.description_mode
        if mode == "developer":
            auth = {
                "auth_mode": "api_key",
                "credentials_file": None,
                "service_account_email": None,
                "service_account_project": None,
            }
            provider = "google_gemini_developer_api"
            project = None
            location = None
        else:
            auth = self._service_account_info()
            provider = "google_vertex_ai" if mode == "vertex" else "fallback"
            if mode == "vertex":
                project = self.google_cloud_project or None
                location = self.google_cloud_location or None
            else:
                project = None
                location = None

        return {
            "enabled": self.description_service_configured,
            "mode": mode,
            "provider": provider,
            "sdk": "google-genai",
            "model": self.description_model,
            "project": project,
            "location": location,
            "auth_mode": auth["auth_mode"],
            "credentials_file": auth["credentials_file"],
            "service_account_email": auth["service_account_email"],
            "service_account_project": auth["service_account_project"],
        }

    def tts_runtime_info(self) -> dict[str, str | bool | None]:
        auth = self._service_account_info()
        return {
            "provider": self.tts_provider,
            "google_credentials_configured": bool(self.google_application_credentials),
            "auth_mode": auth["auth_mode"] if self.tts_provider == "google" else None,
            "credentials_file": auth["credentials_file"] if self.tts_provider == "google" else None,
            "service_account_email": auth["service_account_email"]
            if self.tts_provider == "google"
            else None,
            "service_account_project": auth["service_account_project"]
            if self.tts_provider == "google"
            else None,
        }

    def runtime_snapshot(self) -> dict[str, dict[str, str | bool | None]]:
        return {
            "description": self.description_runtime_info(),
            "tts": self.tts_runtime_info(),
        }


settings = Settings()
