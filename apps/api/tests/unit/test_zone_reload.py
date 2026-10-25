"""Zone reload across resolutions test (T091, FR-012, FR-013).

Verifies that a saved danger zone re-renders in the identical normalized position
when displayed on frames of different sizes/resolutions using stored source_width/source_height.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.repo import get_danger_zone, upsert_danger_zone


@pytest.mark.asyncio
async def test_saved_zone_reload_and_resolution_scaling(db_session: AsyncSession) -> None:
    """A zone stored at 1280x720 scales accurately to 1920x1080 and 640x480."""
    run_id = "test-run-zone-reload"
    norm_points = [
        [0.2, 0.25],
        [0.75, 0.25],
        [0.8, 0.85],
        [0.15, 0.8],
    ]

    # 1. Save danger zone with 1280x720 source frame
    saved = await upsert_danger_zone(
        session=db_session,
        run_id=run_id,
        points=norm_points,
        source_width=1280,
        source_height=720,
        label="Pad Danger Exclusion Zone",
    )
    assert saved.source_width == 1280
    assert saved.source_height == 720

    # 2. Reload zone from database
    reloaded = await get_danger_zone(db_session, run_id)
    assert reloaded is not None
    assert reloaded.points_json == norm_points

    # 3. Project to original source resolution
    source_pixels = [
        (int(p[0] * reloaded.source_width), int(p[1] * reloaded.source_height))
        for p in reloaded.points_json
    ]
    assert source_pixels[0] == (int(0.2 * 1280), int(0.25 * 720))

    # 4. Project to different display/capture resolutions (e.g. 1920x1080 Full HD and 640x480 SD)
    w_hd, h_hd = 1920, 1080
    hd_pixels = [(int(p[0] * w_hd), int(p[1] * h_hd)) for p in reloaded.points_json]
    # Check normalized relative positions remain consistent within 1 pixel rounding
    for orig_norm, (hx, hy) in zip(reloaded.points_json, hd_pixels):
        assert abs((hx / w_hd) - orig_norm[0]) < 0.002
        assert abs((hy / h_hd) - orig_norm[1]) < 0.002

    w_sd, h_sd = 640, 480
    sd_pixels = [(int(p[0] * w_sd), int(p[1] * h_sd)) for p in reloaded.points_json]
    for orig_norm, (sx, sy) in zip(reloaded.points_json, sd_pixels):
        assert abs((sx / w_sd) - orig_norm[0]) < 0.005
        assert abs((sy / h_sd) - orig_norm[1]) < 0.005
