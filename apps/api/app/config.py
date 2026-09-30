"""Application configuration and settings via pydantic-settings (Constitution 2.II, R8)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from rule_engine.config import MIN_CONFIDENCE_FOR_OK
from rule_engine.types import Severity, Thresholds

MANDATED_DISCLAIMER: str = (
    "Decision-support tool. Not a replacement for certified range safety."
)
VERDICT_ATTRIBUTION: str = "Verdict computed by rules; explanation by AI"


class ThresholdsConfig(BaseModel):
    """Configurable thresholds matching rule_engine.types.Thresholds."""

    fin_angle_warning_deg: float = 3.0
    fin_angle_critical_deg: float = 6.0
    fin_angle_error_margin_deg: float = 1.5
    wind_warning_ms: float = 10.0
    wind_critical_ms: float = 15.0
    poor_visibility_severity: Severity = Severity.WARNING
    heavy_precipitation_severity: Severity = Severity.WARNING
    area_not_cleared_severity: Severity = Severity.CRITICAL
    object_in_zone_severity: Severity = Severity.CRITICAL
    motion_sensitivity: float = 0.5
    detector_conf: float = 0.25
    detector_iou: float = 0.45
    zone_occupancy: bool = True

    def to_domain(self) -> Thresholds:
        """Convert to frozen domain dataclass."""
        return Thresholds(
            fin_angle_warning_deg=self.fin_angle_warning_deg,
            fin_angle_critical_deg=self.fin_angle_critical_deg,
            fin_angle_error_margin_deg=self.fin_angle_error_margin_deg,
            wind_warning_ms=self.wind_warning_ms,
            wind_critical_ms=self.wind_critical_ms,
            poor_visibility_severity=self.poor_visibility_severity,
            heavy_precipitation_severity=self.heavy_precipitation_severity,
            area_not_cleared_severity=self.area_not_cleared_severity,
            object_in_zone_severity=self.object_in_zone_severity,
            motion_sensitivity=self.motion_sensitivity,
            detector_conf=self.detector_conf,
            detector_iou=self.detector_iou,
            zone_occupancy=self.zone_occupancy,
        )


class ConfigResponse(BaseModel):
    """Schema returned by GET /api/config."""

    min_confidence_for_ok: float = Field(default=MIN_CONFIDENCE_FOR_OK)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    disclaimer: str = Field(default=MANDATED_DISCLAIMER)


class Settings(BaseSettings):
    """Environment configuration settings for LaunchGuard AI API."""

    database_url: str = Field(default="sqlite+aiosqlite:///./launchguard.db")
    checkpoint_db: str = Field(default="./checkpoints.db")
    media_root: str = Field(default="./media")
    cors_origins: str = Field(default="http://localhost:3000")
    openai_api_key: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")
    openai_timeout_s: float = Field(default=6.0)
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
