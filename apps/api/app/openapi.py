"""OpenAPI schema generator and assembler for contract export (T028, Constitution 3.I)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Assemble complete and strictly typed OpenAPI schema document."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="LaunchGuard AI API",
        version="0.1.0",
        description=(
            "Deterministic safety inspection and pad monitoring API. "
            "Governed by specs/001-launchguard-mvp/contracts/api.md."
        ),
        routes=app.routes,
    )

    # Ensure openapi 3.1.0 specification tag
    openapi_schema["info"]["x-attributions"] = (
        "Verdict computed by rules; explanation by AI. "
        "Decision-support tool. Not a replacement for certified range safety."
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema
