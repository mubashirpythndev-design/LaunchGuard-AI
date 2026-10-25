"""Monitor latency performance test (T078, NFR-002, contracts/api.md).

Verifies that server-side frame processing latency stays strictly under 500 ms.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from cv.models import get_yolo_model

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "images"


@pytest.mark.asyncio
async def test_monitored_frame_processed_under_500ms() -> None:
    """A monitored frame is processed server-side in under 500 ms (NFR-002)."""
    # Pre-warm YOLO singleton to exclude initial disk load overhead
    get_yolo_model()

    app = create_app()
    fixture_path = FIXTURES_DIR / "person_in_zone.jpg"
    assert fixture_path.exists(), f"Fixture missing: {fixture_path}"
    image_bytes = fixture_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create run and zone
        run_res = await client.post("/api/monitor")
        assert run_res.status_code == 201
        run_id = run_res.json()["run_id"]

        zone_res = await client.put(
            f"/api/monitor/{run_id}/zone",
            json={
                "points": [
                    [0.1, 0.1],
                    [0.9, 0.1],
                    [0.9, 0.9],
                    [0.1, 0.9],
                ],
                "label": "Pad test zone",
            },
        )
        assert zone_res.status_code == 200

        # Send frame and measure server-side processing_ms
        frame_res = await client.post(
            f"/api/monitor/{run_id}/frame",
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )
        assert frame_res.status_code == 200
        data = frame_res.json()

        processing_ms = data["processing_ms"]
        assert processing_ms < 500.0, (
            f"Server-side frame processing took {processing_ms:.1f}ms, exceeding 500ms limit"
        )
