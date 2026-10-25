"""Regression coverage for invented rocket regions on unrelated uploads."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from cv.body import inspect_body
from cv.fins import check_fin_alignment
from cv.subject import locate_rocket
from rule_engine.types import Severity
from tests.conftest import FIXTURES_IMAGES


def notebook() -> np.ndarray:
    image = np.full((720, 960, 3), 245, dtype=np.uint8)
    for y in range(60, 700, 35):
        cv2.line(image, (20, y), (940, y), (100, 100, 100), 2)
        cv2.putText(image, "Notes: array values 75, 45, 90", (90, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (160, 45, 30), 2)
    cv2.line(image, (60, 0), (60, 719), (60, 60, 190), 2)
    return image


@pytest.mark.parametrize("kind", ["notebook", "noise", "blank", "landscape", "rectangle"])
def test_unrelated_images_never_get_defect_boxes_or_angles(kind: str) -> None:
    image = notebook()
    if kind == "noise":
        image = np.random.default_rng(42).integers(0, 256, (600, 800, 3), dtype=np.uint8)
    if kind == "blank":
        image = np.full((600, 800, 3), 128, dtype=np.uint8)
    if kind == "landscape":
        image = np.zeros((600, 800, 3), dtype=np.uint8)
        image[:400] = (150, 120, 90)
        image[400:] = (40, 100, 40)
    if kind == "rectangle":
        image = np.full((600, 800, 3), 40, dtype=np.uint8)
        cv2.rectangle(image, (340, 90), (460, 510), (220, 220, 220), -1)
    assert locate_rocket(image) is None
    for finding in inspect_body(image) + check_fin_alignment(image):
        assert finding.severity == Severity.WARNING
        assert finding.degraded
        assert finding.confidence == 0
        assert finding.overlay is None
        assert not any(m.name == "fin_angle_deviation" for m in finding.metrics)


@pytest.mark.parametrize("shift", [-150, 140])
def test_rocket_region_moves_with_pixels_not_image_center(shift: int) -> None:
    image = cv2.imread(str(FIXTURES_IMAGES / "normal.jpg"))
    moved = cv2.warpAffine(image, np.float32([[1, 0, shift], [0, 1, 0]]), (800, 600))
    subject = locate_rocket(moved)
    assert subject is not None
    x1, _, x2, _ = subject.body
    assert abs((x1 + x2) / 2 - (400 + shift)) < 10
    assert check_fin_alignment(moved)[0].metrics[0].value < 3


@pytest.mark.asyncio
async def test_notebook_upload_holds_without_invented_findings_or_reference() -> None:
    success, buffer = cv2.imencode(".jpg", notebook())
    assert success
    content = bytes(buffer)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/inspections", files={
            "file": ("rocket.jpg", content, "image/jpeg"),
        })
        assert response.status_code == 201
        run_id = response.json()["run_id"]
        assert (await client.get(f"/api/runs/{run_id}")).json()["verdict"] == "HOLD"
        findings = (await client.get(f"/api/runs/{run_id}/findings")).json()
        assert findings
        assert all(f["severity"] == "warning" and f["degraded"] for f in findings)
        assert all(f["overlay"] is None for f in findings)
        rocket = (await client.post("/api/rockets", json={
            "name": "Non-rocket baseline", "vehicle_class": "test",
        })).json()
        baseline = await client.post(f"/api/rockets/{rocket['id']}/references/front", files={
            "file": ("rocket.jpg", content, "image/jpeg"),
        })
        assert baseline.status_code == 422
        multi = await client.post("/api/inspections", data={"rocket_id": rocket["id"]}, files={
            angle: (f"{angle}.jpg", content, "image/jpeg")
            for angle in ("front", "right", "back", "left")
        })
        assert multi.status_code == 201
        multi_id = multi.json()["run_id"]
        assert (await client.get(f"/api/runs/{multi_id}")).json()["verdict"] == "HOLD"
        multi_findings = (await client.get(f"/api/runs/{multi_id}/findings")).json()
        assert all(f["severity"] == "warning" and f["degraded"] for f in multi_findings)
        assert all(f["overlay"] is None for f in multi_findings)


@pytest.mark.parametrize("size", [(640, 480), (1000, 750), (800, 600)])
def test_supported_geometry_is_scale_and_fin_color_independent(size: tuple[int, int]) -> None:
    image = cv2.imread(str(FIXTURES_IMAGES / "normal.jpg"))
    image = cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    image = cv2.resize(image, size)
    subject = locate_rocket(image)
    assert subject is not None
    center = (subject.body[0] + subject.body[2]) / 2 / size[0]
    assert abs(center - 0.5) < 0.02


def test_user_screenshot_if_available() -> None:
    screenshot = Path(__file__).resolve().parents[4] / "image.png"
    if not screenshot.exists():
        pytest.skip("User screenshot is a local debugging artifact, not a test dependency")
    image = cv2.imread(str(screenshot))
    assert locate_rocket(image) is None
    assert all(f.degraded and f.overlay is None for f in inspect_body(image))
