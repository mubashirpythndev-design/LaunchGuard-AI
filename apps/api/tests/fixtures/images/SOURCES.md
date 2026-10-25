# Fixture Images Provenance

These test images are synthetically generated for LaunchGuard AI to provide reproducible, zero-external-dependency test fixtures and demo scenarios.

| File | Scenario | Purpose | Expected Verdict |
|---|---|---|---|
| `normal.jpg` | Normal flight vehicle | Symmetrical fins, clear pad | **GO** |
| `fin_misaligned.jpg` | Asymmetrical fin mount | Measured leading-edge asymmetry (>3 deg warn / <=6 deg crit) | **HOLD** |
| `person_in_zone.jpg` | Pad safety breach | Technician detected within danger exclusion zone | **NO-GO** |
| `rocket_reference_front.jpg` | Golden baseline | Stored livery and pristine body surface | Reference |
| `rocket_current_damaged.jpg` | Reference deviation | Same livery with a new fracture | **NO-GO** |
| `rocket_golden_reference.jpg` | Golden baseline | Alias of rocket_reference_front.jpg | Reference |
| `rocket_current_intact.jpg` | Unchanged surface | Same baseline and existing livery | Reference check OK |
| `rocket_current_cracked.jpg` | New surface damage | Alias of rocket_current_damaged.jpg | Reference check critical |

Generated programmatically by `scripts/generate_fixtures.py`.

These are synthetic 800x600 illustrations, not certified hardware photographs.
The reference aliases are byte-identical in the API fixtures and web demo folder.
Reference check OK is not a GO verdict: mandatory manual inputs and every other
finding still participate in the deterministic decision. Four copies of this
single-view illustration demonstrate quadrant routing, not physical 360-degree coverage.
