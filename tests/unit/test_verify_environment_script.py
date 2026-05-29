import importlib.util
from pathlib import Path


def _load_verify_environment_module():
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / "scripts" / "verify_environment.py"
    spec = importlib.util.spec_from_file_location("verify_environment_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_verify_environment_uses_runtime_settings_resolution(tmp_path, monkeypatch):
    """The verifier should read .env with the same root-relative semantics as runtime."""
    module = _load_verify_environment_module()
    importlib.import_module("core.config")

    credentials_path = tmp_path / "creds" / "service-account.json"
    ffmpeg_path = tmp_path / "tools" / "ffmpeg.exe"
    ffprobe_path = tmp_path / "tools" / "ffprobe-custom.exe"
    credentials_path.parent.mkdir()
    ffmpeg_path.parent.mkdir()
    credentials_path.write_text("{}")
    ffmpeg_path.write_text("stub")
    ffprobe_path.write_text("stub")
    (tmp_path / ".env").write_text(
        "GOOGLE_APPLICATION_CREDENTIALS=./creds/service-account.json\n"
        "GOOGLE_CLOUD_PROJECT=prototype-487106\n"
        "FFMPEG_PATH=./tools/ffmpeg.exe\n"
        "FFPROBE_PATH=./tools/ffprobe-custom.exe\n"
    )
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("TTS_PROVIDER", raising=False)
    monkeypatch.delenv("FFMPEG_PATH", raising=False)
    monkeypatch.delenv("FFPROBE_PATH", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    settings = module._load_runtime_settings(tmp_path)
    ffmpeg_cmd, ffprobe_cmd = module._resolve_ffmpeg_commands(settings)

    assert settings.tts_provider == "google"
    assert settings.google_application_credentials == str(credentials_path.resolve())
    assert settings.google_cloud_project == "prototype-487106"
    assert settings.description_mode == "vertex"
    assert ffmpeg_cmd == str(ffmpeg_path.resolve())
    assert ffprobe_cmd == str(ffprobe_path.resolve())


def test_verify_environment_reads_gemini_api_key_mode(tmp_path, monkeypatch):
    module = _load_verify_environment_module()
    importlib.import_module("core.config")

    (tmp_path / ".env").write_text("GEMINI_API_KEY=test-api-key\nTTS_PROVIDER=edge\n")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    settings = module._load_runtime_settings(tmp_path)

    assert settings.description_mode == "developer"
    assert settings.description_runtime_info()["provider"] == "google_gemini_developer_api"
    assert settings.tts_provider == "edge"


def test_verify_environment_runtime_imports_do_not_include_python_multipart():
    """The verifier should only check live runtime dependencies."""
    module = _load_verify_environment_module()

    package_names = {package_name for package_name, _ in module.RUNTIME_IMPORTS}
    import_names = {import_name for _, import_name in module.RUNTIME_IMPORTS}

    assert "python-multipart" not in package_names
    assert "multipart" not in import_names


def test_verify_environment_dev_imports_do_not_include_pip_tools():
    """The verifier should follow the repo's uv-based dev dependency contract."""
    module = _load_verify_environment_module()

    package_names = {package_name for package_name, _ in module.DEV_IMPORTS}
    import_names = {import_name for _, import_name in module.DEV_IMPORTS}

    assert "pip-tools" not in package_names
    assert "piptools" not in import_names
