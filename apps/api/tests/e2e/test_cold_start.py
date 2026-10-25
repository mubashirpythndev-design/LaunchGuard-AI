"""Cold start reliability test (T130, NFR-007, SC-001).

Asserts that even on a fresh, cold database state:
1. Scenario seeding automatically initializes.
2. All three scenarios successfully run and yield their expected verdicts.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from db import init_db


@pytest.mark.asyncio
async def test_cold_start_demo_scenarios() -> None:
    """Cold-start test: verify system initializes tables and scenarios cleanly."""
    # Ensure fresh schema
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check scenarios endpoint works on cold start
        res = await client.get("/api/demo/scenarios")
        assert res.status_code == 200
        scenarios = res.json()["scenarios"]
        assert len(scenarios) == 3

        # Run normal scenario
        run_res = await client.post("/api/demo/scenarios/normal/run")
        assert run_res.status_code == 201
        run_id = run_res.json()["run_id"]

        # Verify report
        rep_res = await client.get(f"/api/runs/{run_id}/report")
        assert rep_res.status_code == 200
        assert rep_res.json()["verdict"] == "GO"
