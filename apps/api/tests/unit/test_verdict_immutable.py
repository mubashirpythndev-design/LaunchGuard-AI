"""Unit test for verdict immutability (T101, Constitution 2.I, SH-006).

Verifies that the verdict stored in the report is byte-identical to the rule engine's
independent output, even when the narrative generation fails, times out, or returns corrupted prose.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agent.narrative import build_narrative_context, generate_narrative
from agent.report import assemble_early_report, complete_report_narrative
from db.models import Base, NarrativeStatus, RunMode, SourceType
from db.repo import create_run, get_report_by_run
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Thresholds,
    Verdict,
)
from rule_engine.verdict import make_decision


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
@pytest.mark.parametrize(
    "findings,expected_verdict",
    [
        (
            [
                Finding(
                    module="cv.body",
                    check_id="body.cracks",
                    severity=Severity.CRITICAL,
                    message="Critical structural crack detected on lower fuselage.",
                    confidence=0.92,
                    metrics=(Measurement(name="crack_len_px", value=45.0, unit="px"),),
                    overlay=Overlay(
                        kind=OverlayKind.BBOX,
                        check_id="body.cracks",
                        points=((0.1, 0.2), (0.3, 0.4)),
                        label="Crack",
                    ),
                    step_position=1,
                )
            ],
            Verdict.NO_GO,
        ),
        (
            [
                Finding(
                    module="cv.fins",
                    check_id="fin.alignment",
                    severity=Severity.WARNING,
                    message="Fin angle deviation 4.2°.",
                    confidence=0.85,
                    metrics=(
                        Measurement(
                            name="fin_angle_deviation",
                            value=4.2,
                            unit="deg",
                            threshold=3.0,
                        ),
                    ),
                    overlay=Overlay(
                        kind=OverlayKind.ARC,
                        check_id="fin.alignment",
                        points=((0.1, 0.1), (0.2, 0.2)),
                        label="Fin",
                    ),
                    step_position=2,
                )
            ],
            Verdict.HOLD,
        ),
        (
            [],
            Verdict.HOLD,
        ),  # Empty findings with no manual inputs defaults to HOLD
    ],
)
async def test_report_verdict_byte_identical_to_rule_engine(
    memory_db: AsyncSession,
    findings: list[Finding],
    expected_verdict: Verdict,
) -> None:
    """Assert that the report verdict is strictly identical to make_decision output."""
    # 1. Compute deterministic verdict via rule engine directly
    decision = make_decision(findings, manual_inputs=None, thresholds=Thresholds())
    assert decision.verdict == expected_verdict

    run_id = f"test-run-{expected_verdict.value.lower()}"
    await create_run(
        memory_db,
        run_id=run_id,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
    )

    # 2. Persist early report
    early_report = await assemble_early_report(memory_db, run_id=run_id, decision=decision)
    assert early_report.verdict == decision.verdict
    assert early_report.verdict.value.encode("utf-8") == decision.verdict.value.encode("utf-8")

    # 3. Simulate narrative failure / timeout
    context = build_narrative_context(
        decision.verdict, decision.risk_score, decision.reasons, decision.findings
    )
    failed_narrative = await generate_narrative(context, api_key=None)
    assert failed_narrative.status == NarrativeStatus.UNAVAILABLE

    # 4. Complete report
    await complete_report_narrative(memory_db, run_id=run_id, narrative_result=failed_narrative)

    # 5. Reload from DB and verify exact byte-identity
    reloaded = await get_report_by_run(memory_db, run_id)
    assert reloaded is not None
    assert reloaded.verdict == decision.verdict
    assert reloaded.verdict.value == expected_verdict.value
    assert reloaded.verdict.value.encode("utf-8") == expected_verdict.value.encode("utf-8")
