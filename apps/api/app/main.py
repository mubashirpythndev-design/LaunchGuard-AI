"""Main FastAPI application entrypoint for LaunchGuard AI.

Constitution 3.I, 3.IV, Research R5, R12.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import get_settings
from app.openapi import custom_openapi
from app.recovery import reconcile_running_runs
from app.routers import config, demo, health, inspections, monitor, runs, share
from db import async_session_factory, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager handling table initialization, checkpointer, and recovery."""
    settings = get_settings()

    # 1. Initialize tables and seed scenarios
    await init_db()

    # 2. Open checkpoint connection and reconcile runs (closes on shutdown per R12)
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db) as checkpointer:
        app.state.checkpointer = checkpointer
        async with async_session_factory() as session:
            await reconcile_running_runs(session, checkpointer)
        yield


def create_app() -> FastAPI:
    """Application factory for LaunchGuard AI API."""
    settings = get_settings()

    app = FastAPI(
        title="LaunchGuard AI API",
        version="0.1.0",
        description="Deterministic safety inspection and pad monitoring API",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(inspections.router)
    app.include_router(monitor.router)
    app.include_router(runs.router)
    app.include_router(share.router)
    app.include_router(demo.router)

    # Custom OpenAPI schema generator
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]

    return app


app = create_app()
