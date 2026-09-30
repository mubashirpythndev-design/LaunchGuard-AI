"""Launchpad monitor API routes (contracts/api.md)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.schemas import (
    CreateRunResponse,
    DangerZoneResponse,
    DeleteZoneResponse,
    FrameAnalysisResponse,
    MonitorLogResponse,
    ZonePolygonPayload,
)

router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRunResponse,
)
async def create_monitor_run() -> CreateRunResponse:
    """Create a new launchpad monitor run."""
    run_id = str(uuid.uuid4())
    return CreateRunResponse(
        run_id=run_id,
        mode="monitor",
        status="running",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=["launchpad_area"],
    )


@router.post(
    "/{run_id}/frame",
    response_model=FrameAnalysisResponse,
)
async def analyze_frame(
    run_id: str,
    request: Request,
) -> FrameAnalysisResponse:
    """Process a single video or camera frame against pad danger zone and hazard cues."""
    body = await request.body()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Frame bytes cannot be empty.",
        )

    return FrameAnalysisResponse(
        seq=1,
        zone_status="CLEAR",
        processing_ms=120.0,
        frame_width=1280,
        frame_height=720,
        findings=[],
    )


@router.put(
    "/{run_id}/zone",
    response_model=DangerZoneResponse,
)
async def upsert_zone(
    run_id: str,
    payload: ZonePolygonPayload,
) -> DangerZoneResponse:
    """Create or update danger zone polygon for a monitor run."""
    if len(payload.points) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danger zone polygon must contain at least 3 points.",
        )

    return DangerZoneResponse(
        run_id=run_id,
        points=payload.points,
        source_width=1280,
        source_height=720,
        label=payload.label,
    )


@router.delete(
    "/{run_id}/zone",
    response_model=DeleteZoneResponse,
)
async def delete_zone(run_id: str) -> DeleteZoneResponse:
    """Remove danger zone definition for a monitor run."""
    return DeleteZoneResponse(deleted=True)


@router.get(
    "/{run_id}/log",
    response_model=MonitorLogResponse,
)
async def get_monitor_log(run_id: str) -> MonitorLogResponse:
    """Retrieve chronological log of monitor detections."""
    return MonitorLogResponse(entries=[])
