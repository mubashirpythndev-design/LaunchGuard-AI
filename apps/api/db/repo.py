"""Data access layer for LaunchGuard AI (Constitution 3.V, data-model.md)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    ChecklistStepModel,
    DangerZoneModel,
    DemoScenarioModel,
    FindingModel,
    ManualInputModel,
    NarrativeStatus,
    ReportModel,
    RocketModel,
    RocketReferenceModel,
    RunEventModel,
    RunMode,
    RunModel,
    RunStatus,
    SourceType,
    StepStatus,
)
from rule_engine.types import Finding, Severity, Verdict


def utc_now() -> datetime:
    return datetime.now(UTC)


async def recover_completed_report(session: AsyncSession, run_id: str) -> ReportModel | None:
    """Repair a missing historical report from stored facts, never rerunning CV or rules.

    Insert-only conflict handling protects an existing report from concurrent requests.
    No verdict, finding, run status or risk score is changed during recovery.
    """
    existing = await get_report_by_run(session, run_id)
    if existing is not None:
        return existing
    run = await get_run(session, run_id)
    if (run is None or run.status != RunStatus.COMPLETED
            or run.verdict is None or run.risk_score is None):
        return None
    findings = await get_findings_by_run(session, run_id)
    steps = await get_checklist_steps(session, run_id)
    reasons = [
        {"check_id": f.check_id, "severity": f.severity.value,
         "message": f.message, "confidence": f.confidence,
         "ambiguous": f.near_threshold_note is not None}
        for f in findings if f.severity != Severity.OK
    ]
    # Older single-image runs kept manual-input reasons only in their completion event.
    events = await get_run_events(session, run_id)
    messages = {reason["message"] for reason in reasons}
    for event in events:
        if event.event_type != "run.completed":
            continue
        recorded_reasons = event.payload_json.get("reasons", [])
        if not isinstance(recorded_reasons, list):
            continue
        for reason in recorded_reasons:
            message = reason.get("message") if isinstance(reason, dict) else reason
            if isinstance(message, str) and message not in messages:
                reasons.append({"check_id": "historical.recorded_reason", "severity": "warning",
                                "message": message, "confidence": 0.0, "ambiguous": False})
                messages.add(message)
    if not reasons:
        reasons = [{"check_id": "historical.report_recovered", "severity": "warning",
                    "message": "Report recovered from stored results; no recorded reason "
                    "was available. Original verdict retained.",
                    "confidence": 0.0, "ambiguous": False}]
    await session.execute(sqlite_insert(ReportModel).values(
        run_id=run_id, verdict=run.verdict, risk_score=run.risk_score,
        reasons_json=reasons,
        checklist_json=[{"position": step.position, "step_key": step.step_key,
                         "label": step.step_key.replace("_", " ").title(),
                         "status": step.status.value,
                         "finding_count": sum(f.step_position == step.position for f in findings)}
                        for step in steps],
        recommended_actions_json=[],
        disclaimer="Decision-support tool. Not a replacement for certified range safety.",
        narrative_status=NarrativeStatus.UNAVAILABLE,
        annotated_ref=f"/api/runs/{run_id}/annotated.png" if run.source_ref else None,
    ).on_conflict_do_nothing(index_elements=["run_id"]))
    await session.commit()
    return await get_report_by_run(session, run_id)


# --- Run Operations ---


async def create_run(
    session: AsyncSession,
    mode: RunMode,
    source_type: SourceType,
    source_ref: str | None = None,
    thresholds_json: dict[str, Any] | None = None,
    frame_width: int | None = None,
    frame_height: int | None = None,
    run_id: str | None = None,
    rocket_id: str | None = None,
) -> RunModel:
    """Create a new run entity."""
    run = RunModel(
        mode=mode,
        source_type=source_type,
        source_ref=source_ref,
        rocket_id=rocket_id,
        thresholds_json=thresholds_json or {},
        frame_width=frame_width,
        frame_height=frame_height,
        status=RunStatus.RUNNING,
        started_at=utc_now(),
    )
    if run_id:
        run.id = run_id
    session.add(run)
    await session.flush()
    return run


async def get_run(session: AsyncSession, run_id: str) -> RunModel | None:
    """Retrieve run by its primary key ID."""
    return await session.get(RunModel, run_id)


async def list_runs(
    session: AsyncSession,
    verdict: Verdict | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[RunModel]:
    """List runs ordered by creation time descending, optionally filtered by verdict."""
    stmt = select(RunModel)
    if verdict is not None:
        stmt = stmt.where(RunModel.verdict == verdict)
    stmt = stmt.order_by(RunModel.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def count_runs(
    session: AsyncSession,
    verdict: Verdict | None = None,
) -> int:
    """Count total runs, optionally filtered by verdict."""
    stmt = select(func.count(RunModel.id))
    if verdict is not None:
        stmt = stmt.where(RunModel.verdict == verdict)
    result = await session.execute(stmt)
    return (result.scalar() or 0)


async def update_run(
    session: AsyncSession,
    run_id: str,
    status: RunStatus | None = None,
    status_reason: str | None = None,
    verdict: Verdict | None = None,
    risk_score: int | None = None,
    completed: bool = False,
) -> RunModel | None:
    """Update status, verdict, or completion timestamp of a run."""
    run = await get_run(session, run_id)
    if not run:
        return None

    if status is not None:
        run.status = status
    if status_reason is not None:
        run.status_reason = status_reason
    if verdict is not None:
        run.verdict = verdict
    if risk_score is not None:
        run.risk_score = risk_score
    if completed:
        run.completed_at = utc_now()

    run.updated_at = utc_now()
    await session.flush()
    return run


# --- Finding Operations ---


async def append_finding(
    session: AsyncSession,
    run_id: str,
    finding: Finding,
    seq: int | None = None,
) -> FindingModel:
    """Append a finding to a run."""
    if seq is None:
        max_seq_stmt = select(func.coalesce(func.max(FindingModel.seq), 0)).where(
            FindingModel.run_id == run_id
        )
        current_seq = (await session.execute(max_seq_stmt)).scalar() or 0
        seq = current_seq + 1

    metrics_list = [
        {
            "name": m.name,
            "value": m.value,
            "unit": m.unit,
            "error_margin": m.error_margin,
            "threshold": m.threshold,
        }
        for m in finding.metrics
    ]

    overlay_dict: dict[str, Any] | None = None
    if finding.overlay:
        overlay_dict = {
            "kind": finding.overlay.kind.value,
            "check_id": finding.overlay.check_id,
            "points": [list(pt) for pt in finding.overlay.points],
            "radius": finding.overlay.radius,
            "start_deg": finding.overlay.start_deg,
            "end_deg": finding.overlay.end_deg,
            "label": finding.overlay.label,
        }

    finding_record = FindingModel(
        run_id=run_id,
        seq=seq,
        module=finding.module,
        check_id=finding.check_id,
        severity=finding.severity,
        message=finding.message,
        confidence=finding.confidence,
        metrics_json=metrics_list,
        overlay_json=overlay_dict,
        step_position=finding.step_position,
        degraded=finding.degraded,
        low_confidence_critical=finding.low_confidence_critical,
        near_threshold_note=finding.near_threshold_note,
        quadrant=finding.quadrant,
    )
    session.add(finding_record)
    await session.flush()
    return finding_record


async def get_findings_by_run(session: AsyncSession, run_id: str) -> Sequence[FindingModel]:
    """Get all findings associated with a run ordered by sequence."""
    stmt = (
        select(FindingModel).where(FindingModel.run_id == run_id).order_by(FindingModel.seq.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# --- Danger Zone Operations ---


async def upsert_danger_zone(
    session: AsyncSession,
    run_id: str,
    points: list[list[float]],
    source_width: int,
    source_height: int,
    label: str | None = None,
) -> DangerZoneModel:
    """Upsert safety danger zone for a given run."""
    stmt = select(DangerZoneModel).where(DangerZoneModel.run_id == run_id)
    zone = (await session.execute(stmt)).scalar_one_or_none()

    if zone:
        zone.points_json = points
        zone.source_width = source_width
        zone.source_height = source_height
        zone.label = label
        zone.updated_at = utc_now()
    else:
        zone = DangerZoneModel(
            run_id=run_id,
            points_json=points,
            source_width=source_width,
            source_height=source_height,
            label=label,
        )
        session.add(zone)

    await session.flush()
    return zone


async def get_danger_zone(session: AsyncSession, run_id: str) -> DangerZoneModel | None:
    """Get danger zone defined for a run."""
    stmt = select(DangerZoneModel).where(DangerZoneModel.run_id == run_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def delete_danger_zone(session: AsyncSession, run_id: str) -> bool:
    """Delete danger zone for a run if present."""
    zone = await get_danger_zone(session, run_id)
    if zone:
        await session.delete(zone)
        await session.flush()
        return True
    return False


# --- Checklist Step Operations ---


async def upsert_checklist_step(
    session: AsyncSession,
    run_id: str,
    position: int,
    step_key: str,
    status: StepStatus,
    finding_ids: list[str] | None = None,
    required_inputs: list[str] | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> ChecklistStepModel:
    """Upsert checklist step row for a run and position."""
    stmt = select(ChecklistStepModel).where(
        ChecklistStepModel.run_id == run_id,
        ChecklistStepModel.position == position,
    )
    step = (await session.execute(stmt)).scalar_one_or_none()

    if step:
        step.step_key = step_key
        step.status = status
        if finding_ids is not None:
            step.finding_ids_json = finding_ids
        if required_inputs is not None:
            step.required_inputs_json = required_inputs
        if started_at is not None:
            step.started_at = started_at
        if finished_at is not None:
            step.finished_at = finished_at
    else:
        step = ChecklistStepModel(
            run_id=run_id,
            position=position,
            step_key=step_key,
            status=status,
            finding_ids_json=finding_ids or [],
            required_inputs_json=required_inputs,
            started_at=started_at,
            finished_at=finished_at,
        )
        session.add(step)

    await session.flush()
    return step


async def init_checklist_steps(session: AsyncSession, run_id: str) -> list[ChecklistStepModel]:
    """Initialize all 5 default checklist steps for a new run."""
    steps = [
        (1, "body"),
        (2, "fins"),
        (3, "launchpad_area"),
        (4, "weather_manual"),
        (5, "decision"),
    ]
    created: list[ChecklistStepModel] = []
    for pos, key in steps:
        step = await upsert_checklist_step(
            session=session,
            run_id=run_id,
            position=pos,
            step_key=key,
            status=StepStatus.PENDING,
        )
        created.append(step)
    return created


async def update_checklist_step(
    session: AsyncSession,
    run_id: str,
    position: int,
    status: StepStatus,
) -> ChecklistStepModel | None:
    """Update status of an existing checklist step."""
    stmt = select(ChecklistStepModel).where(
        ChecklistStepModel.run_id == run_id,
        ChecklistStepModel.position == position,
    )
    step = (await session.execute(stmt)).scalar_one_or_none()
    if step:
        step.status = status
        await session.flush()
    return step


async def get_checklist_steps(session: AsyncSession, run_id: str) -> Sequence[ChecklistStepModel]:
    """Get all checklist steps for a run ordered by position."""
    stmt = (
        select(ChecklistStepModel)
        .where(ChecklistStepModel.run_id == run_id)
        .order_by(ChecklistStepModel.position.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# --- Manual Input Operations ---


async def upsert_manual_input(
    session: AsyncSession,
    run_id: str,
    field: str,
    value: Any,
    rule_fired: Severity | None = None,
) -> ManualInputModel:
    """Upsert a manual input field."""
    stmt = select(ManualInputModel).where(
        ManualInputModel.run_id == run_id,
        ManualInputModel.field == field,
    )
    item = (await session.execute(stmt)).scalar_one_or_none()

    if item:
        item.value_json = value
        item.rule_fired = rule_fired
        item.captured_at = utc_now()
    else:
        item = ManualInputModel(
            run_id=run_id,
            field=field,
            value_json=value,
            rule_fired=rule_fired,
        )
        session.add(item)

    await session.flush()
    return item


async def get_manual_inputs(session: AsyncSession, run_id: str) -> Sequence[ManualInputModel]:
    """Retrieve all manual inputs submitted for a run."""
    stmt = select(ManualInputModel).where(ManualInputModel.run_id == run_id)
    result = await session.execute(stmt)
    return result.scalars().all()


# --- Event Logging Operations ---


async def append_run_event(
    session: AsyncSession,
    run_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> RunEventModel:
    """Append a streaming event with monotonic sequence number."""
    max_seq_stmt = select(func.coalesce(func.max(RunEventModel.seq), 0)).where(
        RunEventModel.run_id == run_id
    )
    current_seq = (await session.execute(max_seq_stmt)).scalar() or 0
    next_seq = current_seq + 1

    event = RunEventModel(
        run_id=run_id,
        seq=next_seq,
        event_type=event_type,
        payload_json=payload,
    )
    session.add(event)
    await session.flush()
    return event


async def get_run_events(
    session: AsyncSession,
    run_id: str,
    after_seq: int = 0,
) -> Sequence[RunEventModel]:
    """Retrieve run events strictly greater than after_seq for SSE replay."""
    stmt = (
        select(RunEventModel)
        .where(RunEventModel.run_id == run_id, RunEventModel.seq > after_seq)
        .order_by(RunEventModel.seq.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# --- Report Operations ---


async def upsert_report(
    session: AsyncSession,
    run_id: str,
    verdict: Verdict,
    risk_score: int,
    reasons: list[str],
    checklist: list[dict[str, Any]],
    recommended_actions: list[str],
    disclaimer: str,
    narrative_status: NarrativeStatus = NarrativeStatus.PENDING,
    narrative_text: str | None = None,
    narrative_model: str | None = None,
    share_token: str | None = None,
    annotated_ref: str | None = None,
) -> ReportModel:
    """Create or update final inspection report."""
    stmt = select(ReportModel).where(ReportModel.run_id == run_id)
    report = (await session.execute(stmt)).scalar_one_or_none()

    if report:
        report.verdict = verdict
        report.risk_score = risk_score
        report.reasons_json = reasons
        report.checklist_json = checklist
        report.recommended_actions_json = recommended_actions
        report.narrative_status = narrative_status
        if narrative_text is not None:
            report.narrative_text = narrative_text
        if narrative_model is not None:
            report.narrative_model = narrative_model
        if share_token is not None:
            report.share_token = share_token
        if annotated_ref is not None:
            report.annotated_ref = annotated_ref
        report.disclaimer = disclaimer
    else:
        report = ReportModel(
            run_id=run_id,
            verdict=verdict,
            risk_score=risk_score,
            reasons_json=reasons,
            checklist_json=checklist,
            recommended_actions_json=recommended_actions,
            narrative_status=narrative_status,
            narrative_text=narrative_text,
            narrative_model=narrative_model,
            disclaimer=disclaimer,
            share_token=share_token,
            annotated_ref=annotated_ref,
        )
        session.add(report)

    await session.flush()
    return report


async def get_report_by_run(session: AsyncSession, run_id: str) -> ReportModel | None:
    """Get report for a run."""
    stmt = select(ReportModel).where(ReportModel.run_id == run_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_report_by_share_token(session: AsyncSession, share_token: str) -> ReportModel | None:
    """Get report by public share token."""
    stmt = select(ReportModel).where(ReportModel.share_token == share_token)
    return (await session.execute(stmt)).scalar_one_or_none()


# --- Demo Scenario Operations ---


async def get_demo_scenario(session: AsyncSession, key: str) -> DemoScenarioModel | None:
    """Get a demo scenario by key."""
    return await session.get(DemoScenarioModel, key)


async def list_demo_scenarios(
    session: AsyncSession,
) -> Sequence[DemoScenarioModel]:
    """List all available demo scenarios ordered by sort order."""
    stmt = select(DemoScenarioModel).order_by(DemoScenarioModel.sort_order.asc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def seed_demo_scenarios(session: AsyncSession) -> None:
    """Seed the default 3 demo scenarios if not present."""
    demos = [
        DemoScenarioModel(
            key="normal",
            label="Nominal Inspection (GO)",
            expected_verdict=Verdict.GO,
            source_ref="demo/normal.jpg",
            manual_inputs_json={
                "wind_speed_ms": 3.5,
                "visibility": "good",
                "precipitation": "none",
                "area_cleared": True,
            },
            zone_points_json=None,
            sort_order=1,
        ),
        DemoScenarioModel(
            key="misaligned_fin",
            label="Fin Misalignment (HOLD)",
            expected_verdict=Verdict.HOLD,
            source_ref="demo/fin_misaligned.jpg",
            manual_inputs_json={
                "wind_speed_ms": 4.0,
                "visibility": "good",
                "precipitation": "none",
                "area_cleared": True,
            },
            zone_points_json=None,
            sort_order=2,
        ),
        DemoScenarioModel(
            key="person_near_pad",
            label="Pad Exclusion Zone Breach (NO-GO)",
            expected_verdict=Verdict.NO_GO,
            source_ref="demo/person_in_zone.jpg",
            manual_inputs_json={
                "wind_speed_ms": 2.0,
                "visibility": "good",
                "precipitation": "none",
                "area_cleared": True,
            },
            zone_points_json=[
                [0.1, 0.1],
                [0.9, 0.1],
                [0.9, 0.9],
                [0.1, 0.9],
            ],
            sort_order=3,
        ),
    ]

    for demo in demos:
        existing = await session.get(DemoScenarioModel, demo.key)
        if not existing:
            session.add(demo)

    await session.flush()


# --- Rocket Profile & Reference Operations ---


async def create_rocket(
    session: AsyncSession,
    name: str,
    vehicle_class: str,
    notes: str | None = None,
    rocket_id: str | None = None,
) -> RocketModel:
    """Create a new rocket vehicle profile."""
    rocket = RocketModel(
        name=name,
        vehicle_class=vehicle_class,
        notes=notes,
    )
    if rocket_id:
        rocket.id = rocket_id
    session.add(rocket)
    await session.flush()
    return rocket


async def get_rocket(session: AsyncSession, rocket_id: str) -> RocketModel | None:
    """Retrieve rocket vehicle by primary key with loaded references."""
    stmt = (
        select(RocketModel)
        .where(RocketModel.id == rocket_id)
        .options(selectinload(RocketModel.references))
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def list_rockets(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[RocketModel]:
    """Retrieve paginated list of rocket profiles ordered by creation time descending."""
    stmt = (
        select(RocketModel)
        .options(selectinload(RocketModel.references))
        .order_by(RocketModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    return res.scalars().all()


async def count_rockets(session: AsyncSession) -> int:
    """Return total count of rocket profiles."""
    stmt = select(func.count(RocketModel.id))
    res = await session.execute(stmt)
    return res.scalar_one()


async def delete_rocket(session: AsyncSession, rocket_id: str) -> bool:
    """Delete a rocket profile and cascaded references."""
    rocket = await session.get(RocketModel, rocket_id)
    if not rocket:
        return False
    await session.delete(rocket)
    await session.flush()
    return True


async def upsert_rocket_reference(
    session: AsyncSession,
    rocket_id: str,
    quadrant: str,
    image_path: str,
    keypoint_count: int = 0,
) -> RocketReferenceModel:
    """Insert or update a baseline golden reference for a vehicle quadrant."""
    stmt = select(RocketReferenceModel).where(
        RocketReferenceModel.rocket_id == rocket_id,
        RocketReferenceModel.quadrant == quadrant,
    )
    res = await session.execute(stmt)
    ref = res.scalar_one_or_none()

    if ref:
        ref.image_path = image_path
        ref.keypoint_count = keypoint_count
        ref.created_at = utc_now()
    else:
        ref = RocketReferenceModel(
            rocket_id=rocket_id,
            quadrant=quadrant,
            image_path=image_path,
            keypoint_count=keypoint_count,
        )
        session.add(ref)

    await session.flush()
    return ref


async def get_rocket_references(
    session: AsyncSession,
    rocket_id: str,
) -> Sequence[RocketReferenceModel]:
    """Retrieve all golden references for a rocket profile."""
    stmt = (
        select(RocketReferenceModel)
        .where(RocketReferenceModel.rocket_id == rocket_id)
        .order_by(RocketReferenceModel.quadrant.asc())
    )
    res = await session.execute(stmt)
    return res.scalars().all()


async def get_rocket_reference_by_quadrant(
    session: AsyncSession,
    rocket_id: str,
    quadrant: str,
) -> RocketReferenceModel | None:
    """Retrieve reference image for a specific rocket quadrant."""
    stmt = select(RocketReferenceModel).where(
        RocketReferenceModel.rocket_id == rocket_id,
        RocketReferenceModel.quadrant == quadrant,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()
