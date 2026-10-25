"""Multi-angle safety contract: attribution, persistence, failure, and immutable criticals."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from numpy.typing import NDArray

from agent.multi_angle import Detector, evaluate_quadrant
from app.main import app
from rule_engine.types import (
    QUADRANTS,
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Quadrant,
    Severity,
    Thresholds,
)
from tests.conftest import FIXTURES_IMAGES


def nominal(image: NDArray[np.uint8], thresholds: Thresholds) -> list[Finding]:
    return [
        Finding(
            module="cv.body",
            check_id="body.cracks",
            severity=Severity.OK,
            confidence=0.9,
            message="No defect appears in the evaluated view.",
            metrics=(Measurement("defect_count", 0, "count"),),
            overlay=Overlay(OverlayKind.BBOX, "body.cracks", ((0.1, 0.1), (0.9, 0.9))),
        )
    ]


async def upload_reference_set(
    client: AsyncClient, rocket_id: str, content: bytes
) -> None:
    for quadrant in QUADRANTS:
        response = await client.post(
            f"/api/rockets/{rocket_id}/references/{quadrant}",
            files={"file": (f"{quadrant}.jpg", content, "image/jpeg")},
        )
        assert response.status_code == 201, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("critical_angle", QUADRANTS)
async def test_any_quadrant_critical_persists_through_manual_completion(
    critical_angle: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()
    original_evaluate = evaluate_quadrant

    async def controlled(
        path: str | None,
        quadrant: Quadrant,
        detector: Detector,
        step: int,
        key: str,
        thresholds: Thresholds,
    ) -> list[Finding]:
        findings = await original_evaluate(path, quadrant, nominal, step, key, thresholds)
        if quadrant == critical_angle and step == 1:
            return [
                replace(
                    findings[0],
                    severity=Severity.CRITICAL,
                    message=f"{quadrant.title()}: Possible structural crack.",
                )
            ]
        return findings

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            rocket = (
                await client.post(
                    "/api/rockets",
                    json={
                        "name": "Quadrant test",
                        "vehicle_class": "Research",
                    },
                )
            ).json()
            content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
            with patch("agent.multi_angle.evaluate_quadrant", side_effect=controlled):
                response = await client.post(
                    "/api/inspections",
                    data={"rocket_id": rocket["id"]},
                    files={q: (f"{q}.jpg", content, "image/jpeg") for q in QUADRANTS},
                )
            assert response.status_code == 201, response.text
            run_id = response.json()["run_id"]
            run = (await client.get(f"/api/runs/{run_id}")).json()
            assert run["status"] == "completed", run
            assert run["verdict"] == "NO-GO"
            assert run["rocket_id"] == rocket["id"]
            assert len(run["quadrants"]) == 4
            findings = (await client.get(f"/api/runs/{run_id}/findings")).json()
            assert len(findings) == 16
            assert {f["quadrant"] for f in findings} == set(QUADRANTS)
            for image in run["quadrants"]:
                assert (await client.get(image["image_url"])).content == content
                assert (await client.get(image["annotated_image_url"])).status_code == 200
            report = (await client.get(f"/api/runs/{run_id}/report")).json()
            assert report["verdict"] == "NO-GO"
            assert len(report["quadrants"]) == 4
            assert {f["quadrant"] for f in report["findings"]} == set(QUADRANTS)
            events = (await client.get(f"/api/runs/{run_id}/events")).json()
            raised = [e for e in events if e["event_type"] == "finding.raised"]
            assert len(raised) == 16
            assert {e["payload"]["quadrant"] for e in raised} == set(QUADRANTS)
            with patch("app.routers.runs.generate_narrative") as narrative:
                from agent.narrative import NarrativeResult
                from db.models import NarrativeStatus

                narrative.return_value = NarrativeResult(
                    status=NarrativeStatus.UNAVAILABLE, text=None, model=None
                )
                manual = await client.post(
                    f"/api/runs/{run_id}/manual-inputs",
                    json={
                        "wind_speed_ms": 1,
                        "visibility": "good",
                        "precipitation": "none",
                        "area_cleared": True,
                    },
                )
            assert manual.status_code == 200, manual.text
            assert (await client.get(f"/api/runs/{run_id}/report")).json()["verdict"] == "NO-GO"
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_missing_angle_is_degraded_and_never_go() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rocket = (
            await client.post(
                "/api/rockets",
                json={
                    "name": "Partial",
                    "vehicle_class": "Research",
                },
            )
        ).json()
        content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        with (
            patch("agent.multi_angle.inspect_body", nominal),
            patch("agent.multi_angle.check_fin_alignment", nominal),
            patch("agent.multi_angle.check_launchpad_clear", nominal),
        ):
            response = await client.post(
                "/api/inspections",
                data={"rocket_id": rocket["id"]},
                files={q: (f"{q}.jpg", content, "image/jpeg") for q in QUADRANTS if q != "back"},
            )
        run_id = response.json()["run_id"]
        run = (await client.get(f"/api/runs/{run_id}")).json()
        assert run["verdict"] == "HOLD", run
        findings = (await client.get(f"/api/runs/{run_id}/findings")).json()
        missing = [f for f in findings if f["quadrant"] == "back"]
        assert len(missing) == 4
        assert all(f["severity"] == "warning" and f["degraded"] for f in missing)
        assert run["quadrants"][2]["image_url"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exception", "empty", "confidence", "timeout"])
async def test_module_failure_is_degraded_warning(failure: str) -> None:
    import time

    def detector(image: NDArray[np.uint8], thresholds: Thresholds) -> list[Finding]:
        if failure == "exception":
            raise RuntimeError("detector unavailable")
        if failure == "timeout":
            time.sleep(0.1)
        if failure == "empty":
            return []
        return [replace(nominal(image, thresholds)[0], confidence=0.1)]

    with patch("agent.multi_angle.CHECK_TIMEOUT_S", 0.01 if failure == "timeout" else 10):
        findings = await evaluate_quadrant(
            str(FIXTURES_IMAGES / "normal.jpg"), "left", detector, 1, "body", Thresholds()
        )
    assert findings[0].severity == Severity.WARNING
    assert findings[0].degraded
    assert findings[0].quadrant == "left"


@pytest.mark.asyncio
async def test_invalid_multi_angle_requests_create_no_run() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        before = (await client.get("/api/runs")).json()["total"]
        content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        image = ("front.jpg", content, "image/jpeg")
        assert (await client.post("/api/inspections", files={"front": image})).status_code == 422
        assert (
            await client.post(
                "/api/inspections", data={"rocket_id": "unknown"}, files={"front": image}
            )
        ).status_code == 404
        rocket = (
            await client.post(
                "/api/rockets",
                json={
                    "name": "Validation",
                    "vehicle_class": "Research",
                },
            )
        ).json()
        data = {"rocket_id": rocket["id"]}
        assert (await client.post("/api/inspections", data=data)).status_code == 422
        assert (
            await client.post("/api/inspections", data=data, files={"file": image, "front": image})
        ).status_code == 422
        for bad, expected in [
            (("bad.png", b"corrupt", "image/png"), 422),
            (("bad.pdf", b"document", "application/pdf"), 415),
            (("large.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg"), 413),
        ]:
            response = await client.post(
                "/api/inspections", data=data, files={"front": image, "back": bad}
            )
            assert response.status_code == expected, response.text
        assert (await client.get("/api/runs")).json()["total"] == before


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_back", [False, True])
async def test_complete_manual_inputs_cannot_hide_missing_coverage(missing_back: bool) -> None:
    from agent.narrative import NarrativeResult
    from db.models import NarrativeStatus

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rocket = (
            await client.post(
                "/api/rockets",
                json={
                    "name": "Manual gate",
                    "vehicle_class": "Research",
                },
            )
        ).json()
        content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        await upload_reference_set(client, rocket["id"], content)
        with (
            patch("agent.multi_angle.inspect_body", nominal),
            patch("agent.multi_angle.check_fin_alignment", nominal),
            patch("agent.multi_angle.check_launchpad_clear", nominal),
        ):
            response = await client.post(
                "/api/inspections",
                data={"rocket_id": rocket["id"]},
                files={
                    q: (f"{q}.jpg", content, "image/jpeg")
                    for q in QUADRANTS
                    if not (q == "back" and missing_back)
                },
            )
        run_id = response.json()["run_id"]
        assert (await client.get(f"/api/runs/{run_id}")).json()["verdict"] == "HOLD"
        with patch(
            "app.routers.runs.generate_narrative",
            return_value=NarrativeResult(
                status=NarrativeStatus.UNAVAILABLE,
                text=None,
                model=None,
            ),
        ):
            response = await client.post(
                f"/api/runs/{run_id}/manual-inputs",
                json={
                    "wind_speed_ms": 1,
                    "visibility": "good",
                    "precipitation": "none",
                    "area_cleared": True,
                },
            )
        assert response.status_code == 200
        assert (await client.get(f"/api/runs/{run_id}")).json()["verdict"] == (
            "HOLD" if missing_back else "GO"
        )


@pytest.mark.asyncio
async def test_manual_clearance_rejected_before_quadrants_finish() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rocket = (
            await client.post(
                "/api/rockets",
                json={
                    "name": "Running gate",
                    "vehicle_class": "Research",
                },
            )
        ).json()
        content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        with patch("app.multi_angle_upload.run_multi_angle"):
            response = await client.post(
                "/api/inspections",
                data={"rocket_id": rocket["id"]},
                files={"front": ("front.jpg", content, "image/jpeg")},
            )
        run_id = response.json()["run_id"]
        manual = await client.post(
            f"/api/runs/{run_id}/manual-inputs",
            json={
                "wind_speed_ms": 1,
                "visibility": "good",
                "precipitation": "none",
                "area_cleared": True,
            },
        )
        assert manual.status_code == 409
        assert (await client.get(f"/api/runs/{run_id}")).json()["verdict"] is None


@pytest.mark.asyncio
async def test_annotation_failure_preserves_critical_verdict() -> None:
    def critical(image: NDArray[np.uint8], thresholds: Thresholds) -> list[Finding]:
        return [replace(nominal(image, thresholds)[0], severity=Severity.CRITICAL)]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rocket = (
            await client.post(
                "/api/rockets",
                json={
                    "name": "Annotation fallback",
                    "vehicle_class": "Research",
                },
            )
        ).json()
        content = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        with (
            patch("agent.multi_angle.inspect_body", critical),
            patch("agent.multi_angle.check_fin_alignment", nominal),
            patch("agent.multi_angle.check_launchpad_clear", nominal),
            patch(
                "agent.multi_angle.render_annotated_image", side_effect=RuntimeError("render error")
            ),
        ):
            response = await client.post(
                "/api/inspections",
                data={"rocket_id": rocket["id"]},
                files={q: (f"{q}.jpg", content, "image/jpeg") for q in QUADRANTS},
            )
        run_id = response.json()["run_id"]
        run = (await client.get(f"/api/runs/{run_id}")).json()
        assert run["status"] == "completed"
        assert run["verdict"] == "NO-GO"
        assert all(q["annotated_image_url"] is None for q in run["quadrants"])
        findings = (await client.get(f"/api/runs/{run_id}/findings")).json()
        degraded = [f for f in findings if f["check_id"] == "annotation.unavailable"]
        assert len(degraded) == 4
        assert all(f["severity"] == "warning" and f["degraded"] for f in degraded)


@pytest.mark.asyncio
async def test_reference_defect_in_one_quadrant_forces_no_go() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rocket = (
            await client.post(
                "/api/rockets",
                json={"name": "Reference gate", "vehicle_class": "Research"},
            )
        ).json()
        baseline = (FIXTURES_IMAGES / "normal.jpg").read_bytes()
        await upload_reference_set(client, rocket["id"], baseline)

        image = cv2.imdecode(np.frombuffer(baseline, np.uint8), cv2.IMREAD_COLOR)
        assert image is not None
        height, width = image.shape[:2]
        cv2.line(
            image,
            (width // 3, height // 4),
            (2 * width // 3, 3 * height // 4),
            (0, 0, 0),
            25,
        )
        cv2.circle(image, (2 * width // 3, height // 3), 50, (0, 0, 0), -1)
        encoded, damaged_buffer = cv2.imencode(".jpg", image)
        assert encoded
        damaged = bytes(damaged_buffer)

        captures = {
            quadrant: (
                f"{quadrant}.jpg",
                damaged if quadrant == "back" else baseline,
                "image/jpeg",
            )
            for quadrant in QUADRANTS
        }
        with (
            patch("agent.multi_angle.inspect_body", nominal),
            patch("agent.multi_angle.check_fin_alignment", nominal),
            patch("agent.multi_angle.check_launchpad_clear", nominal),
        ):
            response = await client.post(
                "/api/inspections",
                data={"rocket_id": rocket["id"]},
                files=captures,
            )
        assert response.status_code == 201, response.text
        run_id = response.json()["run_id"]
        run = (await client.get(f"/api/runs/{run_id}")).json()
        assert run["verdict"] == "NO-GO"

        findings = (await client.get(f"/api/runs/{run_id}/findings")).json()
        back_reference = next(
            finding
            for finding in findings
            if finding["quadrant"] == "back" and finding["module"] == "cv.reference"
        )
        assert back_reference["severity"] == "critical"
        assert back_reference["check_id"] == "reference.structural_deviation"
        assert not back_reference["degraded"]
        back_image = next(item for item in run["quadrants"] if item["quadrant"] == "back")
        for key in ("reference_image_url", "aligned_image_url", "heatmap_image_url"):
            assert back_image[key]
            assert (await client.get(back_image[key])).status_code == 200
