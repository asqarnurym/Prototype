import importlib.util
import json
from pathlib import Path


def _load_export_openapi_module():
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / "scripts" / "export_openapi.py"
    spec = importlib.util.spec_from_file_location("export_openapi_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_export_openapi_is_not_cwd_dependent(monkeypatch, tmp_path):
    """The script should resolve project paths from its own location, not cwd."""
    module = _load_export_openapi_module()
    monkeypatch.chdir(tmp_path)

    output_path = tmp_path / "generated-openapi.json"
    written_path = module.export_openapi(output_path)
    schema = json.loads(written_path.read_text(encoding="utf-8"))

    assert Path(__file__).resolve().parents[2] == module.PROJECT_ROOT
    assert module.OPENAPI_PATH == module.PROJECT_ROOT / "openapi.json"
    assert written_path == output_path
    assert schema["info"]["title"] == "Prototype API"
