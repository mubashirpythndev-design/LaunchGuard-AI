"""Configuration API router (Constitution 2.II, R8, contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import ConfigResponse, ThresholdsConfig
from rule_engine.config import MIN_CONFIDENCE_FOR_OK

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return public configuration including thresholds, confidence floor, and disclaimer."""
    return ConfigResponse(
        min_confidence_for_ok=MIN_CONFIDENCE_FOR_OK,
        thresholds=ThresholdsConfig(),
    )
