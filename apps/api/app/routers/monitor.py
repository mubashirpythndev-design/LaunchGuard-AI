"""Launchpad monitor fast-path API routes (T083, contracts/api.md, NFR-002).

Fast optical monitoring path:
- Pure computer vision: YOLOv8 person detector + cv/zone.py containment test.
- No language model or agent on this path to sustain >= 2 fps / < 500 ms latency.
- Enforces 409 ZONE_NOT_SET if a frame arrives before a danger zone is defined.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    CreateRunResponse,
    DangerZoneResponse,
    DeleteZoneResponse,
    FindingSchema,
    FrameAnalysisResponse,
    MeasurementSchema,
    MonitorLogEntry,
    MonitorLogResponse,
    OverlaySchema,
    ZonePolygonPayload,
)
from cv.frameio import CorruptImageError, decode_image
from cv.models import predict_objects
from cv.zone import is_bbox_inside_polygon, validate_zone_polygon
from db.base import get_db
from db.models import RunMode, SourceType
from db.repo import (
    create_run,
    delete_danger_zone,
    get_danger_zone,
    upsert_danger_zone,
    utc_now,
)
from rule_engine.types import Severity

router = APIRouter(prefix="/api/monitor", tags=["monitor"])

# In-memory per-run telemetry logs and frame sequence tracking
_monitor_logs: dict[str, list[MonitorLogEntry]] = defaultdict(list)
_frame_seqs: dict[str, int] = defaultdict(int)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRunResponse,
)
async def create_monitor_run(
    session: AsyncSession = Depends(get_db),
) -> CreateRunResponse:
    """Create a new launchpad monitor run."""
    run_id = str(uuid.uuid4())
    await create_run(
        session=session,
        run_id=run_id,
        mode=RunMode.MONITOR,
        source_type=SourceType.LIVE_STREAM,
    )
    await session.commit()

    return CreateRunResponse(
        run_id=run_id,
        mode="monitor",
        status="running",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=["launchpad_area"],
    )


@router.put(
    "/{run_id}/zone",
    response_model=DangerZoneResponse,
)
async def upsert_zone(
    run_id: str,
    payload: ZonePolygonPayload,
    session: AsyncSession = Depends(get_db),
) -> DangerZoneResponse:
    """Create or update danger zone polygon for a monitor run."""
    try:
        validate_zone_polygon(payload.points)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_ZONE",
                    "message": str(exc),
                    "field": "points",
                }
            },
        ) from exc

    source_w = 1280
    source_h = 720

    zone = await upsert_danger_zone(
        session=session,
        run_id=run_id,
        points=payload.points,
        source_width=source_w,
        source_height=source_h,
        label=payload.label,
    )
    await session.commit()

    return DangerZoneResponse(
        run_id=run_id,
        points=zone.points_json,
        source_width=zone.source_width,
        source_height=zone.source_height,
        label=zone.label,
    )


@router.delete(
    "/{run_id}/zone",
    response_model=DeleteZoneResponse,
)
async def delete_zone(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> DeleteZoneResponse:
    """Remove danger zone definition for a monitor run."""
    await delete_danger_zone(session, run_id)
    await session.commit()
    return DeleteZoneResponse(deleted=True)


@router.post(
    "/{run_id}/frame",
    response_model=FrameAnalysisResponse,
)
async def analyze_frame(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> FrameAnalysisResponse:
    """Fast-path processing of a single JPEG frame against danger zone (NFR-002, R4)."""
    start_time = time.perf_counter()

    body = await request.body()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": {
                    "code": "EMPTY_FRAME",
                    "message": "Frame bytes cannot be empty.",
                    "field": "body",
                }
            },
        )

    # 1. Assert danger zone is defined for this run (contracts/api.md)
    zone = await get_danger_zone(session, run_id)
    if not zone or not zone.points_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "ZONE_NOT_SET",
                    "message": "No danger zone defined. Pad clearance not verified.",
                    "field": "zone",
                }
            },
        )

    # 2. Decode frame
    try:
        img = decode_image(body)
    except CorruptImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": {
                    "code": "CORRUPT_IMAGE",
                    "message": str(exc),
                    "field": "body",
                }
            },
        ) from exc

    h, w = img.shape[:2]

    # 3. Fast person detection via YOLOv8 (classes=[0] is 'person')
    detections = predict_objects(img, conf=0.25, iou=0.45, classes=[0])

    # 4. Containment testing against danger zone
    findings: list[FindingSchema] = []
    zone_pts = zone.points_json
    has_person_inside = False

    for det in detections:
        inside = is_bbox_inside_polygon(det.bbox_norm, zone_pts)
        x1, y1, x2, y2 = det.bbox_norm

        if inside:
            has_person_inside = True
            findings.append(
                FindingSchema(
                    module="cv.zone",
                    check_id="zone.occupancy",
                    severity=Severity.CRITICAL,
                    message="A person appears to be inside the marked danger zone.",
                    confidence=round(det.confidence, 2),
                    metrics=[
                        MeasurementSchema(
                            name="overlap_ratio",
                            value=1.0,
                            unit="ratio",
                            error_margin=None,
                            threshold=0.0,
                        )
                    ],
                    overlay=OverlaySchema(
                        kind="bbox",
                        check_id="zone.occupancy",
                        points=[[x1, y1], [x2, y2]],
                        label="person in zone",
                    ),
                    step_position=3,
                    degraded=False,
                    low_confidence_critical=False,
                    near_threshold_note=None,
                )
            )
        else:
            findings.append(
                FindingSchema(
                    module="cv.zone",
                    check_id="zone.occupancy",
                    severity=Severity.OK,
                    message="Person detected outside danger zone.",
                    confidence=round(det.confidence, 2),
                    metrics=[
                        MeasurementSchema(
                            name="overlap_ratio",
                            value=0.0,
                            unit="ratio",
                            error_margin=None,
                            threshold=0.0,
                        )
                    ],
                    overlay=OverlaySchema(
                        kind="bbox",
                        check_id="zone.occupancy",
                        points=[[x1, y1], [x2, y2]],
                        label="person outside zone",
                    ),
                    step_position=3,
                    degraded=False,
                    low_confidence_critical=False,
                    near_threshold_note=None,
                )
            )

    # 5. Determine zone status
    if has_person_inside:
        zone_status = "DANGER"
    elif any(f.severity == Severity.WARNING for f in findings):
        zone_status = "WARNING"
    else:
        zone_status = "CLEAR"

    processing_ms = round((time.perf_counter() - start_time) * 1000.0, 1)

    # 6. Update frame sequence and log entry
    _frame_seqs[run_id] += 1
    seq = _frame_seqs[run_id]

    max_sev = "ok"
    if zone_status == "DANGER":
        max_sev = "critical"
    elif zone_status == "WARNING":
        max_sev = "warning"

    entry = MonitorLogEntry(
        at=utc_now().isoformat().replace("+00:00", "Z"),
        zone_status=zone_status,
        check_ids=[f.check_id for f in findings],
        max_severity=max_sev,
    )
    _monitor_logs[run_id].append(entry)

    return FrameAnalysisResponse(
        seq=seq,
        zone_status=zone_status,
        processing_ms=processing_ms,
        frame_width=w,
        frame_height=h,
        findings=findings,
    )


@router.get(
    "/{run_id}/log",
    response_model=MonitorLogResponse,
)
async def get_monitor_log(run_id: str) -> MonitorLogResponse:
    """Retrieve chronological log of monitor detections (oldest first)."""
    return MonitorLogResponse(entries=_monitor_logs.get(run_id, []))
