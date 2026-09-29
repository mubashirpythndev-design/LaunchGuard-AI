# Fixture Images Provenance

These test images are synthetically generated for LaunchGuard AI to provide reproducible, zero-external-dependency test fixtures and demo scenarios.

| File | Scenario | Purpose | Expected Verdict |
|---|---|---|---|
| `normal.jpg` | Normal flight vehicle | Symmetrical fins, clear pad | **GO** |
| `fin_misaligned.jpg` | Asymmetrical fin mount | 7.2 deg fin deviation (>6 deg crit / >3 deg warn) | **HOLD** |
| `person_in_zone.jpg` | Pad safety breach | Technician detected within danger exclusion zone | **NO-GO** |

Generated programmatically by `scripts/generate_fixtures.py`.
