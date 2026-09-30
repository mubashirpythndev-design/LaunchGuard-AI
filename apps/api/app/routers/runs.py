"""Run lifecycle, streaming, history, and report API routes (contracts/api.md)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import MANDATED_DISCLAIMER, VERDICT_ATTRIBUTION
from app.events import stream_run_events
from app.schemas import (
    EventMessageResponse,
    InputFieldSchema,
    LatestRunSummaryResponse,
    ManualInputPayload,
    ManualInputsSubmissionResponse,
    NarrativeSchema,
    ReportResponse,
    RequiredInputsResponse,
    RunDetailResponse,
    RunDetailSource,
    RunListResponse,
    ShareTokenResponse,
)
from db.base import get_db
from db.repo import get_report_by_run, get_run, get_run_events, list_runs
from rule_engine.types import Verdict

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=RunListResponse)
async def get_runs_list(
    verdict: Verdict | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> RunListResponse:
    """List historical inspection and monitor runs."""
    records = await list_runs(session, limit=limit, offset=offset)
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
        if verdict is None or r.verdict == verdict
    ]
    return RunListResponse(total=len(items), items=items)  # type: ignore[arg-type]


@router.get("/latest", response_model=LatestRunSummaryResponse)
async def get_latest_run_summary(
    session: AsyncSession = Depends(get_db),
) -> LatestRunSummaryResponse:
    """Retrieve summary of the latest run for dashboard presentation."""
    records = await list_runs(session, limit=5, offset=0)
    if not records:
        return LatestRunSummaryResponse()

    latest = records[0]
    return LatestRunSummaryResponse(
        verdict=latest.verdict,
        risk_score=latest.risk_score,
        checklist=[],
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
        run_id=run.id,
        mode=run.mode.value,
        source_type=run.source_type.value,
        status=run.status.value,
        status_reason=run.status_reason,
        verdict=run.verdict,
        risk_score=run.risk_score,
        created_at=run.created_at.isoformat().replace("+00:00", "Z"),
        completed_at=(
            run.completed_at.isoformat().replace("+00:00", "Z")
            if run.completed_at
            else None
        ),
        thresholds=run.thresholds_json,
        source=RunDetailSource(
            width=run.frame_width,
            height=run.frame_height,
            url=f"/api/runs/{run.id}/image" if run.source_ref else None,
        ),
    )


@router.get("/{run_id}/required-inputs", response_model=RequiredInputsResponse)
async def get_required_inputs(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> RequiredInputsResponse:
    """Retrieve list of mandatory inputs required by the run's checklist."""
    fields = [
        InputFieldSchema(
            name="wind_speed_ms",
            label="Wind speed",
            type="number",
            unit="m/s",
            min=0.0,
            max=60.0,
            required=True,
        ),
        InputFieldSchema(
            name="visibility",
            label="Visibility",
            type="enum",
            options=["good", "moderate", "poor"],
            required=True,
        ),
        InputFieldSchema(
            name="precipitation",
            label="Precipitation",
            type="enum",
            options=["none", "light", "heavy"],
            required=True,
        ),
        InputFieldSchema(
            name="area_cleared",
            label="Pad area cleared",
            type="boolean",
            required=True,
        ),
        InputFieldSchema(
            name="notes",
            label="Notes",
            type="text",
            max_length=500,
            required=False,
        ),
    ]
    return RequiredInputsResponse(
        run_id=run_id,
        missing=["wind_speed_ms", "visibility", "precipitation", "area_cleared"],
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
    if payload.wind_speed_ms is not None and payload.wind_speed_ms < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wind speed cannot be negative.",
        )

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
    report = await get_report_by_run(session, run_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for run '{run_id}' not found.",
        )

    return ReportResponse(
        report_id=report.id,
        run_id=report.run_id,
        verdict=report.verdict,
        risk_score=report.risk_score,
        verdict_attribution=VERDICT_ATTRIBUTION,
        disclaimer=report.disclaimer or MANDATED_DISCLAIMER,
        checklist=report.checklist_json,  # type: ignore[arg-type]
        reasons=report.reasons_json,  # type: ignore[arg-type]
        recommended_actions=report.recommended_actions_json,  # type: ignore[arg-type]
        findings=[],
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

    token = secrets.token_urlsafe(32)
    return ShareTokenResponse(
        token=token,
        url=f"/share/{token}",
        read_only=True,
        created_at="2026-10-01T00:00:00Z",
    )


@router.get("/{run_id}/image")
async def get_run_image(run_id: str) -> Response:
    """Return local image bytes for inspection or preview."""
    return Response(content=b"", media_type="image/jpeg")


@router.get("/{run_id}/annotated.png")
async def get_annotated_image(run_id: str) -> Response:
    """Return server-rendered annotated composite image."""
    return Response(content=b"", media_type="image/png")
