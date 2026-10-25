"""Unit test for early report write preserving rule outputs across timeout (T116, SH-006).

Asserts that:
1. assemble_early_report commits verdict, risk_score, checklist, and reasons with pending status.
2. A subsequent narrative timeout modifies ONLY narrative columns.
3. Verdict, risk score, checklist, and reasons remain byte-identical before and after the timeout.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent.narrative import NarrativeResult
from agent.report import assemble_early_report, complete_report_narrative
from db.models import Base, NarrativeStatus, RunMode, SourceType
from db.repo import create_run, get_report_by_run
from rule_engine.types import (
    Decision,
    Finding,
    Measurement,
    Severity,
    StepResult,
    Verdict,
)


@pytest.fixture
async def memory_db() -> AsyncSession:
    """Provide an in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_narrative_timeout_preserves_verdict_and_reasons_byte_identically(
    memory_db: AsyncSession,
) -> None:
    """Early report fields remain byte-identical after narrative timeout."""
    finding = Finding(
        module="cv.fins",
        check_id="fin.alignment",
        severity=Severity.WARNING,
        message="Fin angle deviation appears to be 4.2°",
        confidence=0.81,
        metrics=(
            Measurement(
                name="fin_angle_deviation",
                value=4.2,
                unit="deg",
                threshold=3.0,
            ),
        ),
        step_position=2,
    )

    decision = Decision(
        verdict=Verdict.HOLD,
        risk_score=52,
        findings=(finding,),
        checklist=(
            StepResult(position=1, step_key="body", status="passed", finding_count=0),
            StepResult(position=2, step_key="fins", status="failed", finding_count=1),
            StepResult(position=3, step_key="launchpad_area", status="passed", finding_count=0),
            StepResult(position=4, step_key="weather_manual", status="passed", finding_count=0),
            StepResult(position=5, step_key="decision", status="failed", finding_count=0),
        ),
        reasons=("Fin angle deviation appears to be 4.2°",),
        recommended_actions=("Reinspect fin mounts and re-measure alignment.",),
        missing_inputs=(),
        computed_at=None,  # type: ignore[arg-type]
    )

    run_id = "test-run-early-write-idempotence"
    await create_run(
        memory_db,
        run_id=run_id,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )

    # 1. Early write before model invocation
    early_report = await assemble_early_report(memory_db, run_id=run_id, decision=decision)
    assert early_report.narrative_status == NarrativeStatus.PENDING

    # Snapshot serializations
    early_verdict_bytes = early_report.verdict.value.encode("utf-8")
    early_risk = early_report.risk_score
    early_checklist_json = json.dumps(early_report.checklist_json, sort_keys=True)
    early_reasons_json = json.dumps(early_report.reasons_json, sort_keys=True)

    # 2. Simulate narrative timeout
    timeout_result = NarrativeResult(
        status=NarrativeStatus.UNAVAILABLE,
        text=None,
        model=None,
        recommended_actions=None,
    )
    await complete_report_narrative(memory_db, run_id=run_id, narrative_result=timeout_result)

    # 3. Reload report and assert exact byte identity of non-narrative fields
    reloaded = await get_report_by_run(memory_db, run_id)
    assert reloaded is not None
    assert reloaded.narrative_status == NarrativeStatus.UNAVAILABLE

    assert reloaded.verdict.value.encode("utf-8") == early_verdict_bytes
    assert reloaded.risk_score == early_risk
    assert json.dumps(reloaded.checklist_json, sort_keys=True) == early_checklist_json
    assert json.dumps(reloaded.reasons_json, sort_keys=True) == early_reasons_json
