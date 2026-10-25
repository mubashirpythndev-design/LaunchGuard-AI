"""Quadrant evidence survives LangGraph interruption and resumption without re-running CV."""

from dataclasses import replace
from unittest.mock import patch

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.graph import create_inspection_graph
from agent.state import GraphState
from rule_engine.types import QUADRANTS, Quadrant, Severity, Verdict
from tests.conftest import FIXTURES_IMAGES
from tests.contract.test_multi_angle import nominal


@pytest.mark.asyncio
async def test_graph_retains_all_angles_across_manual_interrupt() -> None:
    from agent.multi_angle import Detector, evaluate_quadrant
    from rule_engine.types import Finding, Thresholds

    async def controlled(
        path: str | None,
        quadrant: Quadrant,
        detector: Detector,
        step: int,
        key: str,
        thresholds: Thresholds,
    ) -> list[Finding]:
        findings = await evaluate_quadrant(path, quadrant, nominal, step, key, thresholds)
        if quadrant == "back" and step == 1:
            return [replace(findings[0], severity=Severity.CRITICAL)]
        return findings

    state: GraphState = {
        "run_id": "four-angle-graph",
        "rocket_id": "vehicle",
        "quadrant_paths": {q: str(FIXTURES_IMAGES / "normal.jpg") for q in QUADRANTS},
        "findings": [],
        "manual_inputs": {},
    }
    async with AsyncSqliteSaver.from_conn_string(":memory:") as saver:
        graph = create_inspection_graph(saver)
        config = {"configurable": {"thread_id": "four-angle-graph"}}
        with patch("agent.graph.evaluate_quadrant", side_effect=controlled) as detector:
            paused = await graph.ainvoke(state, config)
            assert "__interrupt__" in paused
            assert {f.quadrant for f in paused["findings"]} == set(QUADRANTS)
            assert len(paused["findings"]) == 16
            calls = detector.call_count
            completed = await graph.ainvoke(
                Command(
                    resume={
                        "wind_speed_ms": 2.0,
                        "visibility": "good",
                        "precipitation": "none",
                        "area_cleared": True,
                    }
                ),
                config,
            )
            assert completed["verdict"] == Verdict.NO_GO
            assert detector.call_count == calls
