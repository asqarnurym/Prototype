import os

import pytest

from core.config import Settings


def _restore_google_credentials_env(original_value):
    if original_value is None:
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    else:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = original_value


def test_settings_auto_selects_google_from_env_file_credentials(tmp_path):
    """Auto-detect should switch to Google after BaseSettings reads .env."""
    original_value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_path = tmp_path / "service-account.json"
    credentials_path.write_text("{}")
    env_path = tmp_path / ".env"
    env_path.write_text("GOOGLE_APPLICATION_CREDENTIALS=./service-account.json\n")

    try:
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        settings = Settings(_env_file=env_path, project_root=tmp_path)
    finally:
        _restore_google_credentials_env(original_value)

    assert settings.tts_provider == "google"
    assert settings.google_application_credentials == str(credentials_path.resolve())


def test_settings_explicit_tts_provider_overrides_autodetect(tmp_path):
    """Explicit TTS_PROVIDER should win even if Google credentials exist."""
    original_value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_path = tmp_path / "service-account.json"
    credentials_path.write_text("{}")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "GOOGLE_APPLICATION_CREDENTIALS=./service-account.json\nTTS_PROVIDER=edge\n"
    )

    try:
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        settings = Settings(_env_file=env_path, project_root=tmp_path)
    finally:
        _restore_google_credentials_env(original_value)

    assert settings.tts_provider == "edge"
    assert settings.google_application_credentials == str(credentials_path.resolve())


def test_settings_missing_credentials_fall_back_to_edge(tmp_path):
    """Auto-detect should not select Google when the credentials file is missing."""
    original_value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    env_path = tmp_path / ".env"
    env_path.write_text("GOOGLE_APPLICATION_CREDENTIALS=./missing.json\n")

    try:
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        settings = Settings(_env_file=env_path, project_root=tmp_path)
    finally:
        _restore_google_credentials_env(original_value)

    assert settings.tts_provider == "edge"
    assert settings.google_application_credentials == str((tmp_path / "missing.json").resolve())


def test_settings_blank_tts_provider_keeps_autodetect(tmp_path):
    """Blank TTS_PROVIDER should behave like unset and preserve auto-detection."""
    original_value = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    credentials_path = tmp_path / "service-account.json"
    credentials_path.write_text("{}")
    env_path = tmp_path / ".env"
    env_path.write_text("GOOGLE_APPLICATION_CREDENTIALS=./service-account.json\nTTS_PROVIDER=\n")

    try:
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
        settings = Settings(_env_file=env_path, project_root=tmp_path)
    finally:
        _restore_google_credentials_env(original_value)

    assert settings.tts_provider == "google"
    assert settings.google_application_credentials == str(credentials_path.resolve())


def test_settings_enable_vertex_description_mode_from_project_config(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("GOOGLE_CLOUD_PROJECT=prototype-487106\n")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    settings = Settings(_env_file=env_path, project_root=tmp_path)

    assert settings.description_service_configured is True
    assert settings.description_mode == "vertex"
    assert settings.google_cloud_location == "global"


def test_settings_enable_gemini_developer_mode_from_api_key(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=test-api-key\n")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    settings = Settings(_env_file=env_path, project_root=tmp_path)

    assert settings.description_service_configured is True
    assert settings.description_mode == "developer"
    assert settings.description_runtime_info()["provider"] == "google_gemini_developer_api"
    assert settings.description_runtime_info()["auth_mode"] == "api_key"
    assert settings.description_runtime_info()["project"] is None


def test_settings_vertex_mode_wins_when_both_vertex_and_api_key_are_present(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "GEMINI_API_KEY=test-api-key\nGOOGLE_CLOUD_PROJECT=prototype-487106\n"
    )

    settings = Settings(_env_file=env_path, project_root=tmp_path)

    assert settings.description_mode == "vertex"
    assert settings.description_runtime_info()["provider"] == "google_vertex_ai"


def test_settings_fallback_description_mode_without_project(tmp_path, monkeypatch):
    original_project = os.environ.get("GOOGLE_CLOUD_PROJECT")

    try:
        os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        settings = Settings(_env_file=None, project_root=tmp_path)
    finally:
        if original_project is None:
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
        else:
            os.environ["GOOGLE_CLOUD_PROJECT"] = original_project

    assert settings.description_service_configured is False
    assert settings.description_mode == "fallback"


def test_settings_reject_invalid_tts_provider(tmp_path):
    """Invalid provider names should fail fast during settings load."""
    env_path = tmp_path / ".env"
    env_path.write_text("TTS_PROVIDER=unsupported\n")

    with pytest.raises(ValueError, match="TTS_PROVIDER must be 'edge' or 'google'"):
        Settings(_env_file=env_path, project_root=tmp_path)


def test_settings_normalize_relative_ffmpeg_path_from_project_root(tmp_path):
    """Relative FFMPEG_PATH from .env should resolve from the project root."""
    ffmpeg_path = tmp_path / "tools" / "ffmpeg.exe"
    ffmpeg_path.parent.mkdir()
    ffmpeg_path.write_text("stub")
    env_path = tmp_path / ".env"
    env_path.write_text("FFMPEG_PATH=./tools/ffmpeg.exe\n")

    settings = Settings(_env_file=env_path, project_root=tmp_path)

    assert settings.ffmpeg_path == str(ffmpeg_path.resolve())


def test_settings_keep_command_style_ffmpeg_path_unchanged(tmp_path):
    """Bare command names should remain command names for PATH lookup."""
    env_path = tmp_path / ".env"
    env_path.write_text("FFMPEG_PATH=ffmpeg.exe\n")

    settings = Settings(_env_file=env_path, project_root=tmp_path)

    assert settings.ffmpeg_path == "ffmpeg.exe"


def test_settings_normalize_relative_ffprobe_path_from_project_root(tmp_path):
    """Relative FFPROBE_PATH from .env should resolve from the project root."""
    ffprobe_path = tmp_path / "tools" / "ffprobe.exe"
    ffprobe_path.parent.mkdir()
    ffprobe_path.write_text("stub")
    env_path = tmp_path / ".env"
    env_path.write_text("FFPROBE_PATH=./tools/ffprobe.exe\n")

    settings = Settings(_env_file=env_path, project_root=tmp_path)

    assert settings.ffprobe_path == str(ffprobe_path.resolve())
