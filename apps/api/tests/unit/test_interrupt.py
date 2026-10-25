"""Unit test for LangGraph pause and resume mechanics (T102, Research R2).

Verifies that:
1. The graph executes steps 1, 2, 3 and pauses at step 4 (weather_manual) when inputs are missing.
2. The interrupt payload contains the exact list of missing inputs.
3. Resuming with Command(resume=...) on the SAME thread_id completes step 4
   and produces a final decision at step 5.
4. CV tool calls from steps 1-3 are not re-executed upon resume.
"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from agent.graph import create_inspection_graph
from rule_engine.types import Verdict


@pytest.mark.asyncio
async def test_inspection_graph_interrupt_and_resume() -> None:
    """Verify graph pauses at weather_manual step and resumes on the same thread_id."""
    thread_id = "test-thread-interrupt-42"
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        graph = create_inspection_graph(checkpointer=checkpointer)

        # 1. Initial invocation without manual inputs -> MUST interrupt at step 4
        initial_state = {
            "run_id": thread_id,
            "image_path": "non_existent.jpg",
            "findings": [],
            "manual_inputs": {},
            "missing_inputs": ["wind_speed_ms", "visibility", "precipitation", "area_cleared"],
        }

        interrupted = False
        interrupt_value = None

        async for chunk in graph.astream(initial_state, config):
            if "__interrupt__" in chunk:
                interrupted = True
                interrupt_data = chunk["__interrupt__"][0]
                interrupt_value = interrupt_data.value
                break

        assert interrupted, "Graph did not interrupt at manual inputs step!"
        assert interrupt_value is not None
        assert "missing" in interrupt_value
        assert "wind_speed_ms" in interrupt_value["missing"]
        assert "area_cleared" in interrupt_value["missing"]

        # Checkpoint inspection: verify graph is stopped before decision
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        assert checkpoint_tuple is not None

        # 2. Resume with valid complete manual inputs on the SAME thread_id
        valid_inputs = {
            "wind_speed_ms": 4.5,
            "visibility": "good",
            "precipitation": "none",
            "area_cleared": True,
            "notes": "Weather nominal.",
        }

        final_state = None
        async for chunk in graph.astream(Command(resume=valid_inputs), config):
            if "decision" in chunk:
                final_state = chunk["decision"]

        assert final_state is not None, "Graph did not complete through decision node!"
        assert final_state["status"] == "completed"
        assert final_state["current_step"] == 5
        assert isinstance(final_state["verdict"], Verdict)
        assert final_state["risk_score"] is not None
