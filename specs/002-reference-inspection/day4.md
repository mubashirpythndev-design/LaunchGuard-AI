# Day 4: Profile enrollment and comparison workspace

Implemented the Day 4 UI scope from `plan.md` without changing the API contract,
CV pipeline, or deterministic verdict calculation.

## Delivered

- Profile enrollment dialog with name, class, notes, and four golden references.
  Existing profiles can enroll or replace their reference set. A failed reference
  upload retains the new profile ID for retry instead of creating a duplicate.
- Four-angle capture station with quadrant tabs, optional alignment stencil,
  explicit camera start/stop, JPEG capture, and file-upload fallback. Camera tracks
  are released on stop and unmount, including delayed permission responses.
  The browser captures pixels only; detection remains server-side.
- Baseline thumbnails, capture previews, and four-image submission validation.
- Pointer-drag and keyboard-range reference comparison on inspection and reports,
  correctly aligned image proportions, difference contours, and heatmap access.
  Reference evidence uses the backend's `cv.reference` module identifier.
- Dark mission-control presentation with decorative MicroSlats, registry-installed
  DecryptedText, and a reduced-motion-aware capture counter. Decision-critical
  components remain static and the safety disclaimer remains visible.

## Using the feature

Open `/inspect`, register a vehicle and its four baselines, or select an existing
profile. Choose an angle before camera capture, or upload each quadrant directly.
Submit all four images. Each result and the saved report provide quadrant-specific
comparison controls when reference alignment evidence is available. Missing or
failed reference alignment retains degraded findings rather than inventing a
comparison or changing the verdict.

## Verification

- Backend: 114 pytest tests; strict mypy across 47 source files; Ruff.
- Frontend: 57 Vitest tests, including camera permission failure, delayed camera
  cleanup, reference module routing, and contour toggling; strict TypeScript; ESLint.
- Next.js production build completed successfully.
- Browser: all 9 Playwright scenarios, including profile enrollment, fake-camera
  capture, inspection/report comparison, mobile overflow and disclaimer checks.
  Desktop and mobile screenshots were inspected.
- The 30-run deterministic demo regression passed independently and in the full
  browser suite. Its batch timeout is 180 seconds; application limits are unchanged.

The available backend virtual environment runs Python 3.12.8; Python 3.11 remains
the specified target and was not independently exercised here. Browser camera
tests use Chromium's fake device; real hardware and permission behavior can vary.
No automated test suite establishes certified safety or guarantees absence of bugs.

Decision-support tool. Not a replacement for certified range safety.
