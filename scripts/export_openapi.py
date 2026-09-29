"""Export OpenAPI JSON schema from the FastAPI app to packages/contract/openapi.json without running a server."""
import json
import os
import sys
from pathlib import Path

# Add apps/api to sys.path so we can import app
repo_root = Path(__file__).resolve().parent.parent
api_dir = repo_root / "apps" / "api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from app.main import app

def main() -> None:
    openapi_schema = app.openapi()
    target_path = repo_root / "packages" / "contract" / "openapi.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema successfully written to {target_path}")

if __name__ == "__main__":
    main()
