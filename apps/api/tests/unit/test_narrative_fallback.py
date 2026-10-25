"""Unit test for narrative degradation and fallback (T100, FR-026, SH-008).

Asserts that with the model forced to fail or timeout:
- The report still carries verdict, risk score, checklist, and reasons
- Marks narrative_status as 'unavailable' rather than omitting it
- Leaves recommended actions populated from rule defaults
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent.narrative import (
    NarrativeContext,
    build_narrative_context,
    generate_narrative,
)
from agent.report import assemble_early_report, complete_report_narrative
from db.models import Base, NarrativeStatus, RunMode, SourceType
from db.repo import create_run
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
async def test_narrative_fallback_when_api_key_missing(memory_db: AsyncSession) -> None:
    """When OPENAI_API_KEY is absent, narrative degrades gracefully to 'unavailable'."""
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

    run_id = "test-run-fallback-1"
    await create_run(
        memory_db,
        run_id=run_id,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )

    # 1. Early report persisted
    report = await assemble_early_report(memory_db, run_id=run_id, decision=decision)
    assert report.narrative_status == NarrativeStatus.PENDING
    assert report.verdict == Verdict.HOLD
    assert report.risk_score == 52

    # 2. Call generate_narrative with no api key
    context: NarrativeContext = build_narrative_context(
        decision.verdict, decision.risk_score, decision.reasons, decision.findings
    )
    narrative_result = await generate_narrative(context, api_key=None)
    assert narrative_result.status == NarrativeStatus.UNAVAILABLE
    assert narrative_result.text is None

    # 3. Complete report with fallback
    updated = await complete_report_narrative(
        memory_db, run_id=run_id, narrative_result=narrative_result
    )
    assert updated.narrative_status == NarrativeStatus.UNAVAILABLE
    assert updated.verdict == Verdict.HOLD
    assert updated.risk_score == 52
    assert len(updated.reasons_json) == 1
    assert len(updated.checklist_json) == 5
    assert len(updated.recommended_actions_json) == 1


@pytest.mark.asyncio
async def test_narrative_fallback_when_model_times_out(memory_db: AsyncSession) -> None:
    """When the LLM call times out or throws an error, status is marked 'unavailable'."""
    decision = Decision(
        verdict=Verdict.GO,
        risk_score=5,
        findings=(),
        checklist=(StepResult(position=5, step_key="decision", status="passed", finding_count=0),),
        reasons=("All evaluated criteria nominal.",),
        recommended_actions=("Proceed with countdown.",),
        missing_inputs=(),
        computed_at=None,  # type: ignore[arg-type]
    )

    run_id = "test-run-fallback-timeout"
    await create_run(
        memory_db,
        run_id=run_id,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )
    await assemble_early_report(memory_db, run_id=run_id, decision=decision)

    # Calling with invalid key/unreachable host forces error/fallback
    context = build_narrative_context(
        decision.verdict, decision.risk_score, decision.reasons, decision.findings
    )
    result = await generate_narrative(context, api_key="sk-test-fake-key", timeout_sec=0.001)
    assert result.status == NarrativeStatus.UNAVAILABLE

    updated = await complete_report_narrative(memory_db, run_id=run_id, narrative_result=result)
    assert updated.narrative_status == NarrativeStatus.UNAVAILABLE
    assert updated.verdict == Verdict.GO
    assert updated.risk_score == 5
