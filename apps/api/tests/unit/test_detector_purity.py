"""Detector order-independence and purity tests (T073, Constitution 2.I, 3.I).

Verifies that detection functions are pure:
Detecting fixture A then fixture B in one process yields a result for B
that is byte-identical to running B in isolation or in a fresh process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from cv.body import inspect_body
from cv.fins import check_fin_alignment
from cv.frameio import decode_image
from rule_engine.types import Finding, Thresholds

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "images"


def serialize_finding_for_comparison(f: Finding) -> dict[str, Any]:
    """Serialize a Finding to a deterministic dictionary for equality and byte comparison."""
    return {
        "module": f.module,
        "check_id": f.check_id,
        "severity": f.severity.value,
        "message": f.message,
        "confidence": round(f.confidence, 4),
        "metrics": [
            {
                "name": m.name,
                "value": round(m.value, 4) if isinstance(m.value, float) else m.value,
                "unit": m.unit,
                "error_margin": m.error_margin,
                "threshold": m.threshold,
            }
            for m in f.metrics
        ],
        "overlay": {
            "kind": f.overlay.kind.value,
            "check_id": f.overlay.check_id,
            "points": [[round(coord, 4) for coord in pt] for pt in f.overlay.points],
            "radius": round(f.overlay.radius, 4) if f.overlay.radius is not None else None,
            "start_deg": round(f.overlay.start_deg, 4) if f.overlay.start_deg is not None else None,
            "end_deg": round(f.overlay.end_deg, 4) if f.overlay.end_deg is not None else None,
            "label": f.overlay.label,
        }
        if f.overlay
        else None,
        "step_position": f.step_position,
        "degraded": f.degraded,
        "low_confidence_critical": f.low_confidence_critical,
        "near_threshold_note": f.near_threshold_note,
    }


def run_pipeline(image_path: Path) -> list[dict[str, Any]]:
    """Decode and execute body and fin detectors on an image."""
    img_bytes = image_path.read_bytes()
    img = decode_image(img_bytes)
    thresholds = Thresholds()

    body_findings = inspect_body(img, thresholds)
    fin_findings = check_fin_alignment(img, thresholds)
    all_findings = body_findings + fin_findings
    return [serialize_finding_for_comparison(f) for f in all_findings]


def test_detector_order_independence_in_process() -> None:
    """Detecting A then B yields the exact same findings as B in isolation."""
    fixture_a = FIXTURES_DIR / "normal.jpg"
    fixture_b = FIXTURES_DIR / "fin_misaligned.jpg"

    assert fixture_a.exists(), f"Fixture A not found: {fixture_a}"
    assert fixture_b.exists(), f"Fixture B not found: {fixture_b}"

    # 1. Evaluate B in clean state
    results_b_isolated = run_pipeline(fixture_b)

    # 2. Evaluate A
    results_a = run_pipeline(fixture_a)
    assert len(results_a) > 0

    # 3. Evaluate B again in same process after A
    results_b_after_a = run_pipeline(fixture_b)

    # 4. Assert findings are identical
    assert results_b_isolated == results_b_after_a
    assert json.dumps(results_b_isolated, sort_keys=True) == json.dumps(
        results_b_after_a, sort_keys=True
    )


def test_detector_purity_across_fresh_process() -> None:
    """Compare in-process result for B after running A against a fresh subprocess result for B."""
    fixture_a = FIXTURES_DIR / "normal.jpg"
    fixture_b = FIXTURES_DIR / "fin_misaligned.jpg"

    # Run A then B in current process
    _ = run_pipeline(fixture_a)
    in_process_b = run_pipeline(fixture_b)
    in_process_json = json.dumps(in_process_b, sort_keys=True)

    # Run B in fresh standalone python subprocess
    subproc_code = f"""
import json
from pathlib import Path
from tests.unit.test_detector_purity import run_pipeline

b_path = Path(r"{fixture_b}")
res = run_pipeline(b_path)
print(json.dumps(res, sort_keys=True))
"""

    subproc = subprocess.run(
        [sys.executable, "-c", subproc_code],
        cwd=str(Path(__file__).resolve().parent.parent.parent),
        capture_output=True,
        text=True,
        check=True,
    )

    fresh_process_json = subproc.stdout.strip()
    assert in_process_json == fresh_process_json
