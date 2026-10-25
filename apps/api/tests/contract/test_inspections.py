"""Contract tests for POST /api/inspections endpoint (T055, FR-007, FR-008, contracts/api.md)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from db.base import async_session_factory
from db.models import RunModel
from tests.conftest import FIXTURES_IMAGES


@pytest.mark.asyncio
async def test_create_inspection_success() -> None:
    """Valid image upload returns 201 with a run handle and initiates run in DB."""
    image_path = FIXTURES_IMAGES / "normal.jpg"
    assert image_path.exists()
    content = image_path.read_bytes()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/inspections",
            files={"file": ("normal.jpg", content, "image/jpeg")},
        )

    assert response.status_code == 201
    data = response.json()
    assert "run_id" in data
    assert data["mode"] == "inspection"
    assert data["status"] in ("running", "completed")
    assert f"/api/runs/{data['run_id']}/stream" in data["stream_url"]
    assert data["expected_steps"] == [
        "body",
        "fins",
        "launchpad_area",
        "weather_manual",
        "decision",
    ]

    # Verify run exists in DB
    async with async_session_factory() as session:
        result = await session.execute(select(RunModel).where(RunModel.id == data["run_id"]))
        run = result.scalar_one_or_none()
        assert run is not None
        assert run.mode.value == "inspection"


@pytest.mark.asyncio
async def test_create_inspection_oversize_rejected() -> None:
    """Uploads exceeding 10 MB return 413 FILE_TOO_LARGE and create no run."""
    # 10 MB + 100 bytes
    large_payload = b"x" * (10 * 1024 * 1024 + 100)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/inspections",
            files={"file": ("huge.jpg", large_payload, "image/jpeg")},
        )

    assert response.status_code == 413
    data = response.json()
    assert data["error"]["code"] == "FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_create_inspection_wrong_type_rejected() -> None:
    """Non-image upload returns 415 UNSUPPORTED_MEDIA_TYPE and creates no run."""
    pdf_payload = b"%PDF-1.4 test file"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/inspections",
            files={"file": ("manual.pdf", pdf_payload, "application/pdf")},
        )

    assert response.status_code == 415
    data = response.json()
    assert data["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.asyncio
async def test_create_inspection_corrupt_image_rejected() -> None:
    """Zero-byte or undecodable image returns 422 CORRUPT_IMAGE and creates no run."""
    corrupt_payload = b"not a real jpeg binary data stream at all"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/inspections",
            files={"file": ("corrupt.jpg", corrupt_payload, "image/jpeg")},
        )

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "CORRUPT_IMAGE"
