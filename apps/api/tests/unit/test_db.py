from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.base import Base
from db.models import RunMode, SourceType, StepStatus
from db.repo import (
    append_finding,
    append_run_event,
    create_run,
    get_checklist_steps,
    get_danger_zone,
    get_demo_scenario,
    get_findings_by_run,
    get_manual_inputs,
    get_report_by_run,
    get_run,
    get_run_events,
    list_demo_scenarios,
    seed_demo_scenarios,
    update_run,
    upsert_checklist_step,
    upsert_danger_zone,
    upsert_manual_input,
    upsert_report,
)
from rule_engine.types import Finding, Measurement, Severity, Verdict


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite async session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_seed_demo_scenarios(test_session: AsyncSession) -> None:
    await seed_demo_scenarios(test_session)
    demos = await list_demo_scenarios(test_session)
    assert len(demos) == 3
    keys = {d.key for d in demos}
    assert keys == {"normal", "misaligned_fin", "person_near_pad"}

    normal = await get_demo_scenario(test_session, "normal")
    assert normal is not None
    assert normal.expected_verdict == Verdict.GO


@pytest.mark.asyncio
async def test_run_crud_and_relationships(test_session: AsyncSession) -> None:
    # 1. Create run
    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
        source_ref="uploads/test.jpg",
    )
    assert run.id is not None

    # 2. Append findings
    finding = Finding(
        module="cv.body",
        check_id="body.cracks",
        severity=Severity.OK,
        message="No crack patterns identified.",
        confidence=0.92,
        metrics=(Measurement("cracks_count", 0.0, "count"),),
    )
    await append_finding(test_session, run.id, finding)
    findings = await get_findings_by_run(test_session, run.id)
    assert len(findings) == 1
    assert findings[0].check_id == "body.cracks"
    assert findings[0].seq == 1

    # 3. Danger zone
    await upsert_danger_zone(
        test_session,
        run_id=run.id,
        points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]],
        source_width=1920,
        source_height=1080,
    )
    fetched_zone = await get_danger_zone(test_session, run.id)
    assert fetched_zone is not None
    assert len(fetched_zone.points_json) == 3

    # 4. Checklist steps
    await upsert_checklist_step(
        test_session,
        run_id=run.id,
        position=1,
        step_key="body",
        status=StepStatus.PASSED,
    )
    steps = await get_checklist_steps(test_session, run.id)
    assert len(steps) == 1
    assert steps[0].step_key == "body"

    # 5. Manual inputs
    await upsert_manual_input(
        test_session,
        run_id=run.id,
        field="wind_speed_ms",
        value=4.5,
        rule_fired=Severity.OK,
    )
    inputs = await get_manual_inputs(test_session, run.id)
    assert len(inputs) == 1
    assert inputs[0].field == "wind_speed_ms"

    # 6. Monotonic events
    e1 = await append_run_event(test_session, run.id, "step_started", {"position": 1})
    e2 = await append_run_event(test_session, run.id, "step_completed", {"position": 1})
    assert e1.seq == 1
    assert e2.seq == 2
    events = await get_run_events(test_session, run.id, after_seq=1)
    assert len(events) == 1
    assert events[0].seq == 2

    # 7. Update run
    await update_run(
        test_session,
        run.id,
        verdict=Verdict.GO,
        risk_score=15,
        completed=True,
    )
    updated = await get_run(test_session, run.id)
    assert updated is not None
    assert updated.verdict == Verdict.GO
    assert updated.risk_score == 15
    assert updated.completed_at is not None

    # 8. Report
    await upsert_report(
        test_session,
        run_id=run.id,
        verdict=Verdict.GO,
        risk_score=15,
        reasons=["All systems nominal."],
        checklist=[{"position": 1, "status": "passed"}],
        recommended_actions=["Proceed with launch."],
        disclaimer="Decision-support tool. Not a replacement for certified range safety.",
    )
    report = await get_report_by_run(test_session, run.id)
    assert report is not None
    assert report.verdict == Verdict.GO
    assert "Decision-support tool" in report.disclaimer


@pytest.mark.asyncio
async def test_confidence_check_constraint(test_session: AsyncSession) -> None:
    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )

    invalid_finding = Finding(
        module="cv.body",
        check_id="body.cracks",
        severity=Severity.OK,
        message="Bad confidence",
        confidence=1.5,
        metrics=(Measurement("count", 0.0, "count"),),
    )

    with pytest.raises(IntegrityError):
        await append_finding(test_session, run.id, invalid_finding)


@pytest.mark.asyncio
async def test_unique_constraints(test_session: AsyncSession) -> None:
    run = await create_run(
        test_session,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )

    # 1. Unique constraint on (run_id, position) in checklist_steps
    from db.models import ChecklistStepModel, RunEventModel

    step1 = ChecklistStepModel(
        run_id=run.id,
        position=1,
        step_key="body",
        status=StepStatus.PENDING,
    )
    step2 = ChecklistStepModel(
        run_id=run.id,
        position=1,
        step_key="body_duplicate",
        status=StepStatus.PENDING,
    )
    test_session.add(step1)
    await test_session.flush()

    test_session.add(step2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()

    # 2. Unique constraint on (run_id, seq) in run_events
    ev1 = RunEventModel(
        run_id=run.id,
        seq=1,
        event_type="test",
        payload_json={},
    )
    ev2 = RunEventModel(
        run_id=run.id,
        seq=1,
        event_type="test_dup",
        payload_json={},
    )
    test_session.add(ev1)
    await test_session.flush()

    test_session.add(ev2)
    with pytest.raises(IntegrityError):
        await test_session.flush()
    await test_session.rollback()
