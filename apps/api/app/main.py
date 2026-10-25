"""Main FastAPI application entrypoint for LaunchGuard AI.

Constitution 3.I, 3.IV, Research R5, R12.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import get_settings
from app.openapi import custom_openapi
from app.recovery import reconcile_running_runs
from app.routers import config, demo, health, inspections, monitor, rockets, runs, share
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
    app.include_router(rockets.router)
    app.include_router(monitor.router)
    app.include_router(runs.router)
    app.include_router(share.router)
    app.include_router(demo.router)

    # Global exception handler enforcing standard error envelope (contracts/api.md)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
        code_map = {
            400: "BAD_REQUEST",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "FILE_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "CORRUPT_IMAGE",
        }
        code = code_map.get(exc.status_code, "ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": str(exc.detail), "field": None}},
        )

    # Custom OpenAPI schema generator
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]

    return app


app = create_app()
