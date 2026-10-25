"""Inspection latency and config threshold reflection tests (T074, NFR-001, Constitution 2.II).

Verifies:
1. A full single-image inspection reaches a fixed verdict in under 5.0 seconds.
2. A GET /api/config round-trip immediately reflects changed threshold configuration.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import (
    ThresholdsConfig,
    get_current_thresholds,
    set_current_thresholds,
)
from app.main import create_app
from cv.models import get_yolo_model

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "images"


@pytest.mark.asyncio
async def test_full_inspection_completes_under_five_seconds() -> None:
    """A complete single-image inspection finishes and reaches verdict in < 5.0s."""
    # Pre-warm YOLO singleton to exclude initial disk I/O and PyTorch import overhead
    get_yolo_model()

    app = create_app()
    fixture_path = FIXTURES_DIR / "normal.jpg"
    assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

    image_bytes = fixture_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        start_time = time.perf_counter()

        response = await client.post(
            "/api/inspections",
            files={"file": ("normal.jpg", image_bytes, "image/jpeg")},
        )

        elapsed = time.perf_counter() - start_time

        assert response.status_code == 201
        data = response.json()
        assert data["mode"] == "inspection"
        assert data["status"] == "completed"

        # Verify fixed verdict in run details
        run_res = await client.get(f"/api/runs/{data['run_id']}")
        assert run_res.status_code == 200
        run_data = run_res.json()
        assert run_data["verdict"] in ("GO", "HOLD", "NO-GO")

        # NFR-001: Execution under 5.0 seconds
        assert elapsed < 5.0, f"Inspection took {elapsed:.2f}s, exceeding 5.0s budget"


@pytest.mark.asyncio
async def test_config_reflects_changed_threshold() -> None:
    """GET /api/config round-trip reflects updated threshold values."""
    app = create_app()
    original_thresholds = get_current_thresholds()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Initial config check
            res1 = await client.get("/api/config")
            assert res1.status_code == 200
            cfg1 = res1.json()
            assert cfg1["thresholds"]["fin_angle_warning_deg"] == 3.0

            # 2. Modify threshold
            updated = ThresholdsConfig(
                fin_angle_warning_deg=4.5,
                fin_angle_critical_deg=7.5,
            )
            set_current_thresholds(updated)

            # 3. Subsequent round-trip reflects updated threshold
            res2 = await client.get("/api/config")
            assert res2.status_code == 200
            cfg2 = res2.json()
            assert cfg2["thresholds"]["fin_angle_warning_deg"] == 4.5
            assert cfg2["thresholds"]["fin_angle_critical_deg"] == 7.5
    finally:
        set_current_thresholds(original_thresholds)
