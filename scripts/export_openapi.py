import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OPENAPI_PATH = PROJECT_ROOT / "openapi.json"


def _load_app():
    from api.server import app

    return app


def export_openapi(output_path: Path = OPENAPI_PATH) -> Path:
    schema = _load_app().openapi()
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"✅ openapi.json exported successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    export_openapi()
