"""Run lifecycle, streaming, history, manual inputs, and report API routes (contracts/api.md)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.graph import INPUT_FIELDS_REGISTRY
from agent.narrative import build_narrative_context, generate_narrative
from agent.report import assemble_early_report, complete_report_narrative
from app.config import MANDATED_DISCLAIMER, VERDICT_ATTRIBUTION, get_settings
from app.events import broadcaster, stream_run_events
from app.quadrants import quadrant_images
from app.schemas import (
    ActionSchema,
    ChecklistStepSchema,
    CreateRunPayload,
    CreateRunResponse,
    EventMessageResponse,
    FindingSchema,
    InputFieldSchema,
    LatestRunSummaryResponse,
    ManualInputPayload,
    ManualInputsSubmissionResponse,
    NarrativeSchema,
    ReasonSchema,
    ReportResponse,
    RequiredInputsResponse,
    RunDetailResponse,
    RunDetailSource,
    RunListResponse,
    ShareTokenResponse,
)
from db.base import get_db
from db.models import (
    FindingModel,
    InspectionImageModel,
    RocketModel,
    RunMode,
    RunStatus,
    SourceType,
    StepStatus,
)
from db.repo import (
    append_finding,
    count_runs,
    create_run,
    get_checklist_steps,
    get_findings_by_run,
    get_manual_inputs,
    get_run,
    get_run_events,
    init_checklist_steps,
    list_runs,
    recover_completed_report,
    update_checklist_step,
    update_run,
    upsert_manual_input,
)
from rule_engine.manual import MANDATORY_FIELDS, evaluate_manual_inputs
from rule_engine.types import (
    Finding,
    ManualInputSet,
    Measurement,
    Overlay,
    OverlayKind,
    Quadrant,
    Severity,
    Thresholds,
    Verdict,
)
from rule_engine.verdict import make_decision

router = APIRouter(prefix="/api/runs", tags=["runs"])

EXPECTED_STEPS = ["body", "fins", "launchpad_area", "weather_manual", "decision"]


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
        "overlay": (
            {
                "kind": f.overlay.kind.value,
                "check_id": f.overlay.check_id,
                "points": [list(pt) for pt in f.overlay.points],
                "radius": f.overlay.radius,
                "start_deg": f.overlay.start_deg,
                "end_deg": f.overlay.end_deg,
                "label": f.overlay.label,
            }
            if f.overlay
            else None
        ),
        "step_position": f.step_position,
        "degraded": f.degraded,
        "low_confidence_critical": f.low_confidence_critical,
        "near_threshold_note": f.near_threshold_note,
        "quadrant": f.quadrant,
    }


def _reconstruct_finding(r: FindingModel) -> Finding:
    metrics = tuple(
        Measurement(
            name=m["name"],
            value=float(m["value"]),
            unit=m.get("unit", ""),
            error_margin=m.get("error_margin"),
            threshold=m.get("threshold"),
        )
        for m in (r.metrics_json or [])
    )
    overlay = None
    if r.overlay_json:
        overlay = Overlay(
            kind=OverlayKind(r.overlay_json["kind"]),
            check_id=r.overlay_json["check_id"],
            points=tuple((float(pt[0]), float(pt[1])) for pt in r.overlay_json.get("points", ())),
            radius=r.overlay_json.get("radius"),
            start_deg=r.overlay_json.get("start_deg"),
            end_deg=r.overlay_json.get("end_deg"),
            label=r.overlay_json.get("label"),
        )
    return Finding(
        module=r.module,
        check_id=r.check_id,
        severity=r.severity,
        message=r.message,
        confidence=r.confidence,
        metrics=metrics,
        overlay=overlay,
        step_position=r.step_position,
        degraded=r.degraded,
        low_confidence_critical=r.low_confidence_critical,
        near_threshold_note=r.near_threshold_note,
        quadrant=r.quadrant,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateRunResponse)
async def create_run_endpoint(
    payload: CreateRunPayload | None = None,
    session: AsyncSession = Depends(get_db),
) -> CreateRunResponse:
    """Create a new run entity (contracts/api.md)."""
    run_id = str(uuid.uuid4())
    req_mode = payload.mode if payload else "inspection"
    req_source = payload.source_type if payload else "image_upload"
    rocket_id = payload.rocket_id if payload else None
    if rocket_id and await session.get(RocketModel, rocket_id) is None:
        raise HTTPException(404, "Registered rocket profile not found.")

    mode_enum = RunMode.MONITOR if req_mode == "monitor" else RunMode.INSPECTION
    source_enum = (
        SourceType.LIVE_STREAM
        if req_source == "live_stream"
        else SourceType.VIDEO_UPLOAD
        if req_source == "video_upload"
        else SourceType.IMAGE_UPLOAD
    )

    await create_run(
        session=session,
        run_id=run_id,
        mode=mode_enum,
        source_type=source_enum,
        rocket_id=rocket_id,
    )
    await init_checklist_steps(session, run_id)

    # Publish run.started event
    await broadcaster.publish(
        run_id,
        "run.started",
        {
            "run_id": run_id,
            "mode": req_mode,
            "source_type": req_source,
            "steps": [
                {"position": 1, "step_key": "body", "label": "Inspect body"},
                {"position": 2, "step_key": "fins", "label": "Check fins"},
                {"position": 3, "step_key": "launchpad_area", "label": "Check launchpad area"},
                {"position": 4, "step_key": "weather_manual", "label": "Weather & manual inputs"},
                {"position": 5, "step_key": "decision", "label": "Generate decision"},
            ],
        },
        session=session,
    )
    await session.commit()

    return CreateRunResponse(
        run_id=run_id,
        mode=req_mode,
        status="running",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=EXPECTED_STEPS,
    )


@router.get("", response_model=RunListResponse)
async def get_runs_list(
    verdict: Verdict | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> RunListResponse:
    """List historical inspection and monitor runs."""
    records = await list_runs(session, verdict=verdict, limit=limit, offset=offset)
    total = await count_runs(session, verdict=verdict)
    items = [
        {
            "run_id": r.id,
            "verdict": r.verdict,
            "risk_score": r.risk_score,
            "status": r.status.value,
            "created_at": r.created_at.isoformat().replace("+00:00", "Z"),
            "max_severity": None,
        }
        for r in records
    ]
    return RunListResponse(total=total, items=items)  # type: ignore[arg-type]


@router.get("/latest", response_model=LatestRunSummaryResponse)
async def get_latest_run_summary(
    session: AsyncSession = Depends(get_db),
) -> LatestRunSummaryResponse:
    """Retrieve summary of the latest run for dashboard presentation."""
    records = await list_runs(session, limit=5, offset=0)
    if not records:
        return LatestRunSummaryResponse()

    latest = records[0]
    steps = await get_checklist_steps(session, latest.id)
    step_labels: dict[str, str] = {
        "body": "Inspect body",
        "fins": "Check fins",
        "launchpad_area": "Check launchpad area",
        "weather_manual": "Weather & manual inputs",
        "decision": "Generate decision",
    }
    checklist = [
        ChecklistStepSchema(
            position=s.position,
            step_key=s.step_key,
            label=step_labels.get(s.step_key, s.step_key),
            status=s.status.value,
            finding_count=len(s.finding_ids_json or []),
        )
        for s in steps
    ]
    return LatestRunSummaryResponse(
        verdict=latest.verdict,
        risk_score=latest.risk_score,
        checklist=checklist,
        latest_runs=[
            {  # type: ignore[misc]
                "run_id": r.id,
                "verdict": r.verdict,
                "risk_score": r.risk_score,
                "status": r.status.value,
                "created_at": r.created_at.isoformat().replace("+00:00", "Z"),
                "max_severity": None,
            }
            for r in records
        ],
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run_detail(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> RunDetailResponse:
    """Retrieve details and status for a specific run."""
    run = await get_run(session, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    return RunDetailResponse(
        rocket_id=run.rocket_id,
        quadrants=await quadrant_images(session, run_id),
        run_id=run.id,
        mode=run.mode.value,
        source_type=run.source_type.value,
        status=run.status.value,
        status_reason=run.status_reason,
        verdict=run.verdict,
        risk_score=run.risk_score,
        created_at=run.created_at.isoformat().replace("+00:00", "Z"),
        completed_at=(
            run.completed_at.isoformat().replace("+00:00", "Z") if run.completed_at else None
        ),
        thresholds=run.thresholds_json,
        source=RunDetailSource(
            width=run.frame_width,
            height=run.frame_height,
            url=f"/api/runs/{run.id}/image" if run.source_ref else None,
        ),
    )


@router.get("/{run_id}/findings", response_model=list[FindingSchema])
async def get_run_findings(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[FindingSchema]:
    """Retrieve findings associated with a run."""
    records = await get_findings_by_run(session, run_id)
    return [
        FindingSchema(
            module=r.module,
            check_id=r.check_id,
            severity=r.severity,
            message=r.message,
            confidence=r.confidence,
            metrics=r.metrics_json or [],  # type: ignore[arg-type]
            overlay=r.overlay_json,  # type: ignore[arg-type]
            step_position=r.step_position,
            degraded=r.degraded,
            low_confidence_critical=r.low_confidence_critical,
            near_threshold_note=r.near_threshold_note,
            quadrant=r.quadrant,
        )
        for r in records
    ]


@router.get("/{run_id}/required-inputs", response_model=RequiredInputsResponse)
async def get_required_inputs(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> RequiredInputsResponse:
    """Retrieve list of mandatory inputs required by the run's checklist."""
    run = await get_run(session, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    stored_inputs = await get_manual_inputs(session, run_id)
    input_dict = {inp.field: inp.value_json for inp in stored_inputs}
    missing = [f for f in MANDATORY_FIELDS if input_dict.get(f) is None]

    fields = [InputFieldSchema(**f) for f in INPUT_FIELDS_REGISTRY]
    return RequiredInputsResponse(
        run_id=run_id,
        missing=missing,
        fields=fields,
    )


@router.post(
    "/{run_id}/manual-inputs",
    response_model=ManualInputsSubmissionResponse,
)
async def submit_manual_inputs(
    run_id: str,
    payload: ManualInputPayload,
    session: AsyncSession = Depends(get_db),
) -> ManualInputsSubmissionResponse:
    """Submit manual environmental and pad clearance inputs to resume inspection."""
    run = await get_run(session, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )
    if run.rocket_id and (run.completed_at is None or run.status == RunStatus.FAILED):
        raise HTTPException(409, "Wait for all quadrant checks to finish before manual clearance.")

    # 1. Validation (negative wind speed, out-of-range, etc.)
    if payload.wind_speed_ms is not None:
        if payload.wind_speed_ms < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_MANUAL_INPUT",
                        "message": "Wind speed cannot be negative.",
                        "field": "wind_speed_ms",
                    }
                },
            )
        if payload.wind_speed_ms > 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_MANUAL_INPUT",
                        "message": "Wind speed cannot exceed 60 m/s.",
                        "field": "wind_speed_ms",
                    }
                },
            )

    if payload.visibility is not None and payload.visibility not in ("good", "moderate", "poor"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_MANUAL_INPUT",
                    "message": "Visibility must be 'good', 'moderate', or 'poor'.",
                    "field": "visibility",
                }
            },
        )

    if payload.precipitation is not None and payload.precipitation not in (
        "none",
        "light",
        "heavy",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_MANUAL_INPUT",
                    "message": "Precipitation must be 'none', 'light', or 'heavy'.",
                    "field": "precipitation",
                }
            },
        )

    # 2. Persist inputs to manual_inputs table
    if payload.wind_speed_ms is not None:
        await upsert_manual_input(session, run_id, "wind_speed_ms", payload.wind_speed_ms)
    if payload.visibility is not None:
        await upsert_manual_input(session, run_id, "visibility", payload.visibility)
    if payload.precipitation is not None:
        await upsert_manual_input(session, run_id, "precipitation", payload.precipitation)
    if payload.area_cleared is not None:
        await upsert_manual_input(session, run_id, "area_cleared", payload.area_cleared)
    if payload.notes is not None:
        await upsert_manual_input(session, run_id, "notes", payload.notes)

    # 3. Check for remaining missing mandatory inputs
    stored = await get_manual_inputs(session, run_id)
    input_dict = {inp.field: inp.value_json for inp in stored}
    missing = [f for f in MANDATORY_FIELDS if input_dict.get(f) is None]

    fields_schemas = [InputFieldSchema(**f) for f in INPUT_FIELDS_REGISTRY]

    if missing:
        # Partial submission accepted, stays paused
        await update_run(session, run_id=run_id, status=RunStatus.PAUSED)
        await broadcaster.publish(
            run_id,
            "run.awaiting_input",
            {"missing": missing, "fields": INPUT_FIELDS_REGISTRY},
            session=session,
        )
        await session.commit()
        return ManualInputsSubmissionResponse(
            status="paused",
            missing=missing,
            fields=fields_schemas,
        )

    # 4. All mandatory inputs complete -> Resume pipeline
    await update_run(session, run_id=run_id, status=RunStatus.RUNNING)

    # Step 4: Evaluate manual rules
    manual_set = ManualInputSet(
        wind_speed_ms=input_dict.get("wind_speed_ms"),
        visibility=input_dict.get("visibility"),
        precipitation=input_dict.get("precipitation"),
        area_cleared=input_dict.get("area_cleared"),
        notes=input_dict.get("notes"),
    )
    manual_findings = evaluate_manual_inputs(manual_set)
    for mf in manual_findings:
        await append_finding(session, run_id, mf)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(mf), session=session)

    step4_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in manual_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 4, step4_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {
            "position": 4,
            "step_key": "weather_manual",
            "status": step4_status.value,
            "finding_count": len(manual_findings),
        },
        session=session,
    )

    # Step 5: Generate decision
    await broadcaster.publish(
        run_id,
        "checklist.step.started",
        {"position": 5, "step_key": "decision", "label": "Generate decision"},
        session=session,
    )
    await update_checklist_step(session, run_id, 5, StepStatus.RUNNING)

    finding_records = await get_findings_by_run(session, run_id)
    all_findings = [_reconstruct_finding(r) for r in finding_records]
    thresholds = Thresholds()
    decision = make_decision(all_findings, manual_inputs=manual_set, thresholds=thresholds)

    step5_status = StepStatus.PASSED if decision.verdict == Verdict.GO else StepStatus.FAILED
    await update_checklist_step(session, run_id, 5, step5_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {"position": 5, "step_key": "decision", "status": step5_status.value, "finding_count": 0},
        session=session,
    )

    # Persist early report (verdict & reasons fixed BEFORE narrative)
    annotated_url = f"/api/runs/{run_id}/annotated.png" if run.source_ref else None
    report = await assemble_early_report(
        session, run_id=run_id, decision=decision, annotated_ref=annotated_url
    )

    await update_run(
        session,
        run_id=run_id,
        status=RunStatus.COMPLETED,
        verdict=decision.verdict,
        risk_score=decision.risk_score,
        completed=True,
    )

    # Emit run.completed
    await broadcaster.publish(
        run_id,
        "run.completed",
        {
            "verdict": decision.verdict.value,
            "risk_score": decision.risk_score,
            "report_id": report.id,
            "narrative": {"status": "pending"},
            "reasons": report.reasons_json,
        },
        session=session,
    )

    # Narrative generation (with timeout and fallback)
    settings = get_settings()
    context = build_narrative_context(
        decision.verdict, decision.risk_score, decision.reasons, decision.findings
    )
    narrative_result = await generate_narrative(context, api_key=settings.openai_api_key)
    report = await complete_report_narrative(
        session, run_id=run_id, narrative_result=narrative_result
    )

    # Emit report.narrative_ready
    await broadcaster.publish(
        run_id,
        "report.narrative_ready",
        {
            "narrative": {
                "status": report.narrative_status.value,
                "text": report.narrative_text,
                "model": report.narrative_model,
            }
        },
        session=session,
    )

    await session.commit()
    return ManualInputsSubmissionResponse(
        status="running",
        missing=[],
        fields=[],
    )


@router.get("/{run_id}/events", response_model=list[EventMessageResponse])
async def get_events(
    run_id: str,
    after: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> list[EventMessageResponse]:
    """Retrieve JSON event log for a run strictly greater than 'after' sequence."""
    events = await get_run_events(session, run_id, after_seq=after)
    return [
        EventMessageResponse(
            seq=e.seq,
            event_type=e.event_type,
            payload=e.payload_json,
            at=e.created_at.isoformat().replace("+00:00", "Z"),
        )
        for e in events
    ]


@router.get("/{run_id}/stream")
async def stream_events(
    run_id: str,
    last_event_id: Annotated[int | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Stream real-time Server-Sent Events with reconnection support."""
    seq_start = last_event_id or 0
    return StreamingResponse(
        stream_run_events(run_id, last_event_id=seq_start),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/report", response_model=ReportResponse)
async def get_report(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Retrieve final generated report for a completed run."""
    report = await recover_completed_report(session, run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for run '{run_id}' not found.",
        )

    finding_records = await get_findings_by_run(session, run_id)
    findings = [
        FindingSchema(
            module=r.module,
            check_id=r.check_id,
            severity=r.severity,
            message=r.message,
            confidence=r.confidence,
            metrics=r.metrics_json or [],  # type: ignore[arg-type]
            overlay=r.overlay_json,  # type: ignore[arg-type]
            step_position=r.step_position,
            degraded=r.degraded,
            low_confidence_critical=r.low_confidence_critical,
            near_threshold_note=r.near_threshold_note,
            quadrant=r.quadrant,
        )
        for r in finding_records
    ]

    run = await get_run(session, run_id)
    return ReportResponse(
        rocket_id=run.rocket_id if run else None,
        quadrants=await quadrant_images(session, run_id),
        report_id=report.id,
        run_id=report.run_id,
        verdict=report.verdict,
        risk_score=report.risk_score,
        verdict_attribution=VERDICT_ATTRIBUTION,
        disclaimer=report.disclaimer or MANDATED_DISCLAIMER,
        checklist=[ChecklistStepSchema(**s) for s in report.checklist_json],
        reasons=[
            ReasonSchema(**r)
            if isinstance(r, dict)
            else ReasonSchema(
                check_id="generic",
                severity=Severity.WARNING,
                message=str(r),
                confidence=1.0,
            )
            for r in (report.reasons_json or [])
        ],
        recommended_actions=[
            ActionSchema(**a)
            if isinstance(a, dict)
            else ActionSchema(check_id="generic", action=str(a))
            for a in (report.recommended_actions_json or [])
        ],
        findings=findings,
        narrative=NarrativeSchema(
            status=report.narrative_status.value,
            text=report.narrative_text,
            model=report.narrative_model,
        ),
        annotated_image_url=report.annotated_ref,
        generated_at=report.generated_at.isoformat().replace("+00:00", "Z"),
        share_token=report.share_token,
    )


@router.post("/{run_id}/share", response_model=ShareTokenResponse)
async def create_share_link(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> ShareTokenResponse:
    """Generate or retrieve public view token for a completed run report."""
    import secrets

    report = await recover_completed_report(session, run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found or has no completed report.",
        )

    if not report.share_token:
        token = secrets.token_urlsafe(32)
        report.share_token = token
        await session.commit()
    else:
        token = report.share_token

    return ShareTokenResponse(
        token=token,
        url=f"/share/{token}",
        read_only=True,
        created_at=report.generated_at.isoformat().replace("+00:00", "Z"),
    )


@router.get(
    "/{run_id}/quadrants/{quadrant}/{variant}",
    response_class=Response,
    responses={200: {"content": {
        "image/jpeg": {}, "image/png": {}, "image/webp": {},
    }, "description": "Original quadrant image or server-rendered annotation"}},
)
async def get_quadrant_image(
    run_id: str,
    quadrant: Quadrant,
    variant: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    record = await session.scalar(select(InspectionImageModel).where(
        InspectionImageModel.run_id == run_id, InspectionImageModel.quadrant == quadrant,
    ))
    variants = {
        "image": None,
        "annotated": ".annotated.jpg",
        "aligned": ".aligned.jpg",
        "heatmap": ".heatmap.jpg",
    }
    if record is None or record.image_path is None or variant not in variants:
        raise HTTPException(404, "Quadrant image not available.")
    path = Path(record.image_path)
    suffix = variants[variant]
    if suffix:
        path = path.with_suffix(suffix)
    if not path.is_file():
        raise HTTPException(404, "Quadrant image not available.")
    return Response(
        path.read_bytes(),
        media_type=record.content_type if variant == "image" else "image/jpeg",
    )


@router.get("/{run_id}/image")
async def get_run_image(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Return local image bytes for inspection or preview."""
    settings = get_settings()
    img_path = Path(settings.media_root) / "runs" / f"{run_id}.jpg"
    if img_path.exists():
        return Response(content=img_path.read_bytes(), media_type="image/jpeg")

    # Fallback to source_ref if available (e.g. demo run or seeded fixture)
    run = await get_run(session, run_id)
    if run and run.source_ref:
        for candidate in (
            Path(run.source_ref),
            Path("tests/fixtures/images") / Path(run.source_ref).name,
            Path("tests/fixtures/images") / run.source_ref,
        ):
            if candidate.exists():
                return Response(content=candidate.read_bytes(), media_type="image/jpeg")

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run image not found.")


@router.get("/{run_id}/annotated.png")
async def get_annotated_image(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Return server-rendered annotated composite image."""
    settings = get_settings()
    img_path = Path(settings.media_root) / "runs" / f"{run_id}_annotated.jpg"
    if img_path.exists():
        return Response(content=img_path.read_bytes(), media_type="image/jpeg")

    # Fallback to unannotated original image if available
    raw_path = Path(settings.media_root) / "runs" / f"{run_id}.jpg"
    if raw_path.exists():
        return Response(content=raw_path.read_bytes(), media_type="image/jpeg")

    # Fallback to source_ref if available
    run = await get_run(session, run_id)
    if run and run.source_ref:
        for candidate in (
            Path(run.source_ref),
            Path("tests/fixtures/images") / Path(run.source_ref).name,
            Path("tests/fixtures/images") / run.source_ref,
        ):
            if candidate.exists():
                return Response(content=candidate.read_bytes(), media_type="image/jpeg")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Annotated image not found.",
    )
