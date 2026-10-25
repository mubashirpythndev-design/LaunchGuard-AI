"""Startup reconciliation for runs interrupted across process restarts.

Implements Research R12 and Constitution 2.II:
A run interrupted at a manual input checkpoint becomes 'paused'.
A run that crashed mid-step becomes 'failed' with 'interrupted_by_restart'
and never produces a verdict.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RunModel, RunStatus
from db.repo import append_run_event


async def reconcile_running_runs(
    session: AsyncSession,
    checkpointer: Any | None = None,
) -> None:
    """Reconcile runs left in 'running' state when service starts up."""
    stmt = select(RunModel).where(RunModel.status == RunStatus.RUNNING)
    result = await session.execute(stmt)
    running_runs = result.scalars().all()

    for run in running_runs:
        is_interrupted = False
        if checkpointer is not None:
            config = {"configurable": {"thread_id": run.id}}
            checkpoint_tuple = await checkpointer.aget_tuple(config)
            if checkpoint_tuple is not None:
                # Check for interrupts on tasks
                tasks = getattr(checkpoint_tuple, "tasks", ())
                for task in tasks:
                    if getattr(task, "interrupts", ()):
                        is_interrupted = True
                        break
                # Also check metadata or pending writes if available
                metadata = getattr(checkpoint_tuple, "metadata", {}) or {}
                if metadata.get("source") == "interrupt" or metadata.get("interrupted"):
                    is_interrupted = True

        if is_interrupted:
            run.status = RunStatus.PAUSED
        else:
            run.status = RunStatus.FAILED
            run.status_reason = "interrupted_by_restart"
            # Ensure verdict remains None
            run.verdict = None
            await append_run_event(
                session=session,
                run_id=run.id,
                event_type="run.failed",
                payload={
                    "reason": "interrupted_by_restart",
                    "message": (
                        "This run was interrupted when the service restarted and was "
                        "not completed. No verdict was produced."
                    ),
                },
            )

    await session.commit()
