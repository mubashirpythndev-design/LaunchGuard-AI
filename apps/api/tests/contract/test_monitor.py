"""Contract tests for launchpad monitor endpoints (T077, contracts/api.md, NFR-002).

Covers:
- POST /api/monitor (creates monitor run)
- POST /api/monitor/{run_id}/frame before zone returns 409 ZONE_NOT_SET
- PUT /api/monitor/{run_id}/zone with invalid points returns 400 INVALID_ZONE
- PUT /api/monitor/{run_id}/zone with valid points succeeds
- POST /api/monitor/{run_id}/frame returns findings, zone_status, and processing_ms
- DELETE /api/monitor/{run_id}/zone removes the zone
- GET /api/monitor/{run_id}/log returns chronological telemetry logs
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from cv.models import get_yolo_model

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "images"


@pytest.mark.asyncio
async def test_create_monitor_run_returns_201() -> None:
    """POST /api/monitor creates a run in monitor mode."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/monitor")
        assert response.status_code == 201
        data = response.json()
        assert "run_id" in data
        assert data["mode"] == "monitor"
        assert data["status"] == "running"
        assert f"/api/runs/{data['run_id']}/stream" in data["stream_url"]


@pytest.mark.asyncio
async def test_frame_before_zone_returns_409() -> None:
    """POST /api/monitor/{run_id}/frame before a zone is saved returns 409 ZONE_NOT_SET."""
    app = create_app()
    fixture_path = FIXTURES_DIR / "normal.jpg"
    assert fixture_path.exists()
    image_bytes = fixture_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        run_res = await client.post("/api/monitor")
        assert run_res.status_code == 201
        run_id = run_res.json()["run_id"]

        # Attempt to analyze frame without setting a zone first
        frame_res = await client.post(
            f"/api/monitor/{run_id}/frame",
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )
        assert frame_res.status_code == 409
        err = frame_res.json()["error"]
        assert err["code"] == "ZONE_NOT_SET"
        assert "No danger zone defined" in err["message"]


@pytest.mark.asyncio
async def test_zone_upsert_validation_and_frame_analysis() -> None:
    """Test full zone lifecycle: validation reject, save, analyze frame, and delete."""
    # Pre-warm model to ensure fast execution
    get_yolo_model()

    app = create_app()
    fixture_path = FIXTURES_DIR / "person_in_zone.jpg"
    assert fixture_path.exists()
    image_bytes = fixture_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create run
        run_res = await client.post("/api/monitor")
        run_id = run_res.json()["run_id"]

        # 2. Reject malformed zone (fewer than 3 points)
        bad_zone = await client.put(
            f"/api/monitor/{run_id}/zone",
            json={"points": [[0.1, 0.1], [0.9, 0.9]], "label": "Too few points"},
        )
        assert bad_zone.status_code == 400
        assert bad_zone.json()["error"]["code"] == "INVALID_ZONE"

        # 3. Save valid zone covering majority of frame
        valid_zone = await client.put(
            f"/api/monitor/{run_id}/zone",
            json={
                "points": [
                    [0.05, 0.05],
                    [0.95, 0.05],
                    [0.95, 0.95],
                    [0.05, 0.95],
                ],
                "label": "Pad danger zone",
            },
        )
        assert valid_zone.status_code == 200
        zone_data = valid_zone.json()
        assert zone_data["source_width"] == 1280
        assert zone_data["source_height"] == 720
        assert len(zone_data["points"]) == 4

        # 4. Analyze frame with person
        frame_res = await client.post(
            f"/api/monitor/{run_id}/frame",
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )
        assert frame_res.status_code == 200
        frame_data = frame_res.json()
        assert frame_data["seq"] == 1
        assert frame_data["zone_status"] in ("CLEAR", "WARNING", "DANGER")
        assert frame_data["processing_ms"] > 0
        assert frame_data["frame_width"] > 0
        assert frame_data["frame_height"] > 0
        assert isinstance(frame_data["findings"], list)

        # 5. Check monitor log
        log_res = await client.get(f"/api/monitor/{run_id}/log")
        assert log_res.status_code == 200
        log_data = log_res.json()
        assert len(log_data["entries"]) >= 1
        entry = log_data["entries"][0]
        assert "at" in entry
        assert "zone_status" in entry

        # 6. Delete zone and verify subsequent frame returns 409
        del_res = await client.delete(f"/api/monitor/{run_id}/zone")
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True

        frame_after_del = await client.post(
            f"/api/monitor/{run_id}/frame",
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )
        assert frame_after_del.status_code == 409
