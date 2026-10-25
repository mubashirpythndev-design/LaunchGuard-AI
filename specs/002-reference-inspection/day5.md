# Day 5: Verification, design gates, and demo fixtures

## Scope

Regenerated the synthetic fixture set using `scripts/generate_fixtures.py` and
regenerated the OpenAPI contract with `pnpm generate`. Generated contract source
was not hand-edited. Verdict and agent implementations are unchanged.

Visual review exposed an OpenCV erosion-border artifact: invalid frame-edge pixels
were contributing to deviation and could become the largest displayed contour.
The overlap mask now explicitly erodes against a zero-valued exterior with enough
margin for SSIM's neighborhood. Thresholds are unchanged. The fixture damage was
made deliberately large enough to independently exceed the existing critical area
threshold without relying on border artifacts. Tests assert that its contour lies
in the central damaged region rather than at an image edge. The reported area is
relative to valid overlapping image pixels, not a segmented airframe surface or a
physical crack measurement.

The fixture provenance now documents all reference aliases, shared livery, and
the distinction between a reference finding and the overall launch verdict.
New parameterized backend tests exercise the actual shipped baseline/intact/cracked
JPEGs, check repeatability, dimensions, aliases, and API/web byte parity. The intact
pair yields reference OK; the damaged pair yields a non-degraded critical finding
with an overlay. These tests do not establish sensitivity to real hairline cracks.

The new Playwright scenario enrolls the shipped baseline, uploads an intact image
to three angles and damage to Back, and verifies NO-GO in both inspection and saved
report. It checks keyboard slider operation, actual contour geometry, disclaimer
visibility, and absence of browser page errors. Its screenshot is written to
`test-results/day5-cracked-reference.png`.

README and pitch materials now describe the reference demonstration and its limits.
Unsupported certification/compliance wording was removed. Repeated copies of one
synthetic view are explicitly a routing demonstration, not physical 360-degree coverage.

## Verification environment

Verification on 2026-10-18:

- 116 backend tests passed after the border-mask correction.
- Strict mypy passed across 47 source files; Ruff passed.
- All 57 frontend tests passed, including design-lint and React Bits safety boundaries.
- Frontend TypeScript and ESLint passed.
- OpenAPI/contract generation and Next.js production build passed.
- All 10 Playwright scenarios passed against the production build after the fix.
- The cracked-reference browser scenario passed against the production web server;
  its screenshot was reviewed to confirm that the contour marks the central damage.

The installed virtual environment runs Python 3.12.8, not the specified Python 3.11.
No Python 3.11 interpreter was available through the Windows Python launcher.
Ruff now targets Python 3.11 syntax. Mypy's existing Python 3.12 target is retained:
the installed NumPy stubs use Python 3.12 type statements, so forcing a 3.11 target
in this environment fails inside the dependency before checking project code.
A Python 3.11 environment with compatible dependencies is still needed for that gate.
Physical cameras and representative flight hardware are not part of these checks.
Browser camera coverage uses Chromium's fake device.

PowerShell may block `pnpm.ps1`; use `pnpm.cmd` without changing execution policy.
The sandbox denied pytest access to its temporary directory; the full suite was
rerun with access rather than weakening tests. Next.js font fetching also needs
network access during the production build; runtime demo operation does not use it.

Decision-support tool. Not a replacement for certified range safety.
