"""Pre-launch inspection API routes (T066, FR-007, FR-008, contracts/api.md).

Validates file type, size, and decodability before creating a run.
Executes the deterministic inspection pipeline across body, fin, and launchpad modules.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from agent.report import assemble_early_report
from agent.tools import check_launchpad_clear
from app.config import get_settings
from app.events import broadcaster
from app.multi_angle_upload import create_multi_angle
from app.schemas import CreateRunResponse
from cv.annotate import render_annotated_image
from cv.body import inspect_body
from cv.fins import check_fin_alignment
from cv.frameio import CorruptImageError, decode_image
from cv.subject import locate_rocket, unavailable
from db.base import get_db
from db.models import NarrativeStatus, RunMode, RunStatus, SourceType, StepStatus
from db.repo import (
    append_finding,
    create_run,
    init_checklist_steps,
    update_checklist_step,
    update_run,
)
from rule_engine import Finding, Thresholds, compute_risk_score, make_decision

router = APIRouter(prefix="/api/inspections", tags=["inspections"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit (FR-007)
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")


def _serialize_finding(f: Finding) -> dict[str, Any]:
    return {
        "module": f.module,
        "check_id": f.check_id,
        "severity": f.severity.value,
        "message": f.message,
        "confidence": f.confidence,
        "metrics": [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "error_margin": m.error_margin,
                "threshold": m.threshold,
            }
            for m in f.metrics
        ],
        "overlay": {
            "kind": f.overlay.kind.value,
            "check_id": f.overlay.check_id,
            "points": [list(pt) for pt in f.overlay.points],
            "radius": f.overlay.radius,
            "start_deg": f.overlay.start_deg,
            "end_deg": f.overlay.end_deg,
            "label": f.overlay.label,
        }
        if f.overlay
        else None,
        "step_position": f.step_position,
        "degraded": f.degraded,
        "low_confidence_critical": f.low_confidence_critical,
        "near_threshold_note": f.near_threshold_note,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRunResponse,
)
async def create_inspection(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    rocket_id: str | None = Form(default=None),
    front: UploadFile | None = File(default=None),
    right: UploadFile | None = File(default=None),
    back: UploadFile | None = File(default=None),
    left: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_db),
) -> CreateRunResponse:
    """Initiate a pre-launch inspection run from an uploaded rocket image."""
    if rocket_id is not None or any((front, right, back, left)):
        if file is not None:
            raise HTTPException(422, "Choose either single-image or quadrant uploads.")
        if not rocket_id:
            raise HTTPException(422, "A registered rocket_id is required for quadrant uploads.")
        return await create_multi_angle(
            rocket_id, {"front": front, "right": right, "back": back, "left": left},
            session, background_tasks,
        )
    if file is None:
        raise HTTPException(422, "Provide an image or rocket_id and quadrant images.")
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": {
                    "code": "UNSUPPORTED_MEDIA_TYPE",
                    "message": (
                        f"Only JPG, PNG, and WebP images are accepted. Received: {content_type}."
                    ),
                    "field": "file",
                }
            },
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"Upload size {len(content)} bytes exceeds 10 MB limit.",
                    "field": "file",
                }
            },
        )

    try:
        img = decode_image(content)
    except CorruptImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": {
                    "code": "CORRUPT_IMAGE",
                    "message": f"Image is unreadable or corrupted: {exc}",
                    "field": "file",
                }
            },
        ) from exc

    h, w = img.shape[:2]
    run_id = str(uuid.uuid4())
    thresholds = Thresholds()

    # Save original image to disk
    settings = get_settings()
    media_dir = Path(settings.media_root) / "runs"
    media_dir.mkdir(parents=True, exist_ok=True)
    raw_image_path = media_dir / f"{run_id}.jpg"
    raw_image_path.write_bytes(content)

    # 1. Create run entity in DB
    await create_run(
        session=session,
        run_id=run_id,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
        source_ref=str(raw_image_path),
        frame_width=w,
        frame_height=h,
    )
    await init_checklist_steps(session, run_id)

    # 2. Publish run.started event
    await broadcaster.publish(
        run_id,
        "run.started",
        {
            "run_id": run_id,
            "mode": "inspection",
            "source_type": "image_upload",
            "frame_width": w,
            "frame_height": h,
        },
        session=session,
    )

    # 3. Execute step 1: body inspection
    await broadcaster.publish(
        run_id, "step.started", {"position": 1, "step_key": "body"}, session=session
    )
    await update_checklist_step(session, run_id, 1, StepStatus.RUNNING)
    body_findings: list[Finding] = inspect_body(img, thresholds)
    for f in body_findings:
        await append_finding(session, run_id, f)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(f), session=session)

    step1_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in body_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 1, step1_status)
    await broadcaster.publish(
        run_id,
        "step.completed",
        {"position": 1, "step_key": "body", "status": step1_status.value},
        session=session,
    )

    # 4. Execute step 2: fin alignment
    await broadcaster.publish(
        run_id, "step.started", {"position": 2, "step_key": "fins"}, session=session
    )
    await update_checklist_step(session, run_id, 2, StepStatus.RUNNING)
    fin_findings: list[Finding] = check_fin_alignment(img, thresholds)
    for f in fin_findings:
        await append_finding(session, run_id, f)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(f), session=session)

    step2_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in fin_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 2, step2_status)
    await broadcaster.publish(
        run_id,
        "step.completed",
        {"position": 2, "step_key": "fins", "status": step2_status.value},
        session=session,
    )

    # 5. Execute step 3: launchpad clearance
    await broadcaster.publish(
        run_id, "step.started", {"position": 3, "step_key": "launchpad_area"}, session=session
    )
    await update_checklist_step(session, run_id, 3, StepStatus.RUNNING)
    pad_findings: list[Finding] = (
        check_launchpad_clear(img, thresholds=thresholds)
        if locate_rocket(img) is not None else [unavailable(
            "cv.pad", "pad.subject_unverified", 3,
            "The uploaded image could not be established as a supported rocket inspection view.",
        )]
    )
    for f in pad_findings:
        await append_finding(session, run_id, f)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(f), session=session)

    step3_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in pad_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 3, step3_status)
    await broadcaster.publish(
        run_id,
        "step.completed",
        {"position": 3, "step_key": "launchpad_area", "status": step3_status.value},
        session=session,
    )

    # Mark manual inputs step as passed for pure image inspection (or pending manual inputs)
    await update_checklist_step(session, run_id, 4, StepStatus.PASSED)
    await update_checklist_step(session, run_id, 5, StepStatus.PASSED)

    all_findings = body_findings + fin_findings + pad_findings

    # 6. Render annotated image and persist
    annotated_bytes = render_annotated_image(img, all_findings)
    annotated_image_path = media_dir / f"{run_id}_annotated.jpg"
    annotated_image_path.write_bytes(annotated_bytes)

    # 7. Evaluate verdict and risk score
    decision = make_decision(all_findings, manual_inputs=None, thresholds=thresholds)
    risk_score = compute_risk_score(decision.findings, decision.verdict)

    # 8. Update run record to COMPLETED
    await update_run(
        session=session,
        run_id=run_id,
        status=RunStatus.COMPLETED,
        verdict=decision.verdict,
        risk_score=risk_score,
        completed=True,
    )

    report = await assemble_early_report(
        session, run_id, decision, annotated_ref=f"/api/runs/{run_id}/annotated.png"
    )
    # This path does not schedule an LLM call. Do not leave a permanently pending narrative.
    report.narrative_status = NarrativeStatus.UNAVAILABLE

    await broadcaster.publish(
        run_id,
        "run.completed",
        {
            "run_id": run_id,
            "verdict": decision.verdict.value,
            "risk_score": risk_score,
            "report_id": report.id,
            "reasons": report.reasons_json,
        },
        session=session,
    )

    await session.commit()

    return CreateRunResponse(
        run_id=run_id,
        mode="inspection",
        status="completed",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=["body", "fins", "launchpad_area", "weather_manual", "decision"],
    )
