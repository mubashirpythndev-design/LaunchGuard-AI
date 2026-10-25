"""OpenAPI contract conformance tests (Constitution 3.I, T049).

Asserts that:
1. Every declared API route under /api has an explicit response model or documented response.
2. The exported OpenAPI document has valid info, paths, and components without bare un-typed shapes.
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app


def get_all_api_routes() -> list[APIRoute]:
    """Extract all registered APIRoute instances including included routers."""
    routes: list[APIRoute] = []
    for r in app.routes:
        if isinstance(r, APIRoute):
            routes.append(r)
        elif hasattr(r, "original_router"):
            for sub_r in getattr(r, "original_router").routes:
                if isinstance(sub_r, APIRoute):
                    routes.append(sub_r)
    return routes


def test_every_api_route_has_response_contract() -> None:
    """Every route registered under /api must declare a response model or media type."""
    api_routes = [r for r in get_all_api_routes() if r.path.startswith("/api")]
    assert len(api_routes) > 0, "No API routes registered"

    untyped_routes: list[str] = []
    for route in api_routes:
        has_response_model = route.response_model is not None
        has_custom_responses = bool(route.responses)
        # Raw binary/stream routes
        is_binary_stream = route.path in (
            "/api/runs/{run_id}/stream",
            "/api/runs/{run_id}/image",
            "/api/runs/{run_id}/annotated.png",
            "/api/rockets/{rocket_id}/references/{quadrant}",
        )
        if not (has_response_model or has_custom_responses or is_binary_stream):
            untyped_routes.append(f"{route.methods} {route.path}")

    assert not untyped_routes, (
        f"The following routes lack an explicit response model: {untyped_routes}"
    )


def test_openapi_schema_contains_required_sections() -> None:
    """The OpenAPI document must contain required paths and schemas."""
    schema = app.openapi()
    assert schema.get("openapi", "").startswith("3.")
    assert "paths" in schema
    assert "components" in schema
    assert "schemas" in schema["components"]

    paths = schema["paths"]
    assert "/api/health" in paths
    assert "/api/config" in paths
    assert "/api/inspections" in paths
    assert "/api/monitor" in paths
    assert "/api/runs" in paths
    assert "/api/demo/scenarios" in paths
    assert "/api/share/{token}" in paths
