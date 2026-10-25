"""Contract tests for /api/rockets endpoints (specs/002-reference-inspection)."""

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.conftest import FIXTURES_IMAGES


@pytest.mark.asyncio
async def test_create_and_list_rockets() -> None:
    """Create a rocket profile and verify it appears in the list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create
        res = await client.post(
            "/api/rockets",
            json={
                "name": "Falcon-9 Test Vehicle",
                "vehicle_class": "orbital-medium",
                "notes": "Flight article for pre-launch staging verification",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["name"] == "Falcon-9 Test Vehicle"
        assert data["vehicle_class"] == "orbital-medium"
        assert data["reference_count"] == 0
        rocket_id = data["id"]

        # Get by ID
        get_res = await client.get(f"/api/rockets/{rocket_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == rocket_id

        # List
        list_res = await client.get("/api/rockets")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert any(r["id"] == rocket_id for r in list_data["items"])


@pytest.mark.asyncio
async def test_upload_and_retrieve_reference_image() -> None:
    """Upload a valid golden reference image for a quadrant and retrieve it."""
    image_path = FIXTURES_IMAGES / "normal.jpg"
    assert image_path.exists()
    content = image_path.read_bytes()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create rocket
        res = await client.post(
            "/api/rockets",
            json={"name": "Starship SN15", "vehicle_class": "heavy-lift"},
        )
        assert res.status_code == 201
        rocket_id = res.json()["id"]

        # Upload reference for 'front'
        upload_res = await client.post(
            f"/api/rockets/{rocket_id}/references/front",
            files={"file": ("normal.jpg", content, "image/jpeg")},
        )
        assert upload_res.status_code == 201
        ref_data = upload_res.json()
        assert ref_data["quadrant"] == "front"
        assert ref_data["rocket_id"] == rocket_id
        assert ref_data["keypoint_count"] > 0
        assert ref_data["image_url"] == f"/api/rockets/{rocket_id}/references/front"

        # Verify rocket detail reflects 1 reference
        detail_res = await client.get(f"/api/rockets/{rocket_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["reference_count"] == 1
        assert detail["references"][0]["quadrant"] == "front"

        # Retrieve raw image
        img_res = await client.get(f"/api/rockets/{rocket_id}/references/front")
        assert img_res.status_code == 200
        assert "image/" in img_res.headers.get("content-type", "")
        assert len(img_res.content) > 0


@pytest.mark.asyncio
async def test_upload_reference_invalid_quadrant_rejected() -> None:
    """Upload with an unrecognized quadrant returns 400 Bad Request."""
    image_path = FIXTURES_IMAGES / "normal.jpg"
    content = image_path.read_bytes()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/rockets",
            json={"name": "Electron Booster", "vehicle_class": "small-sat"},
        )
        rocket_id = res.json()["id"]

        upload_res = await client.post(
            f"/api/rockets/{rocket_id}/references/top_diagonal",
            files={"file": ("normal.jpg", content, "image/jpeg")},
        )
        assert upload_res.status_code == 400


@pytest.mark.asyncio
async def test_reference_below_minimum_dimensions_is_rejected() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rocket = (
            await client.post(
                "/api/rockets",
                json={"name": "Small reference", "vehicle_class": "research"},
            )
        ).json()
        success, encoded = cv2.imencode(
            ".jpg", np.full((479, 639, 3), 127, dtype=np.uint8)
        )
        assert success
        upload = await client.post(
            f"/api/rockets/{rocket['id']}/references/front",
            files={"file": ("small.jpg", bytes(encoded), "image/jpeg")},
        )
        assert upload.status_code == 422
        assert "at least 640x480" in upload.text
