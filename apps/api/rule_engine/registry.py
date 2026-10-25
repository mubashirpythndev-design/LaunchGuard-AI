"""Stable check registry and step mapping for LaunchGuard AI (Constitution 2.III, Research R6)."""

from __future__ import annotations

from typing import Final

# 5 Ordered Checklist Steps
STEPS: Final[list[dict[str, str | int]]] = [
    {"position": 1, "step_key": "body", "label": "Inspect body"},
    {"position": 2, "step_key": "fins", "label": "Check fins"},
    {"position": 3, "step_key": "launchpad_area", "label": "Check launchpad area"},
    {"position": 4, "step_key": "weather_manual", "label": "Weather & manual inputs"},
    {"position": 5, "step_key": "decision", "label": "Generate decision"},
]

STEP_MAP: Final[dict[int, dict[str, str | int]]] = {int(s["position"]): s for s in STEPS}

# 15 Stable Check IDs mapped to their step position
CHECK_TO_STEP: Final[dict[str, int]] = {
    # Step 1: Body
    "body.cracks": 1,
    "body.dents": 1,
    "body.damage": 1,
    "body.burn_marks": 1,
    "body.missing_parts": 1,
    # Step 2: Fins
    "fin.alignment": 2,
    # Step 3: Launchpad Area & Cues
    "zone.occupancy": 3,
    "cue.smoke": 3,
    "cue.fire": 3,
    "cue.leak": 3,
    "cue.motion": 3,
    # Step 4: Weather & Manual Inputs
    "manual.wind": 4,
    "manual.visibility": 4,
    "manual.precipitation": 4,
    "manual.area_cleared": 4,
}

CHECK_LABELS: Final[dict[str, str]] = {
    "body.cracks": "Surface cracks",
    "body.dents": "Body denting",
    "body.damage": "Surface damage",
    "body.burn_marks": "Dark/burn marks",
    "body.missing_parts": "Missing fasteners/hardware",
    "fin.alignment": "Fin alignment",
    "zone.occupancy": "Pad exclusion zone",
    "cue.smoke": "Smoke indication",
    "cue.fire": "Flame indication",
    "cue.leak": "Liquid pooling/leak",
    "cue.motion": "Abnormal movement",
    "manual.wind": "Surface wind speed",
    "manual.visibility": "Atmospheric visibility",
    "manual.precipitation": "Precipitation conditions",
    "manual.area_cleared": "Range clearance status",
}
