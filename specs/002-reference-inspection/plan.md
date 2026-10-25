# Implementation Plan: Golden Reference & Multi-Angle Inspection

**Branch**: `002-reference-inspection` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)  
**Parent Plan**: `specs/001-launchguard-mvp/plan.md`  
**Constitution**: `.specify/memory/constitution.md` (v1.0.0)

---

## 1. Summary

This plan extends LaunchGuard AI from single-frame inspection to **reference-based anomaly verification and multi-angle 360° vehicle coverage**. 
- In `apps/api`, a new `Rocket` and `RocketReference` entity model stores factory-certified baselines for 4 vehicle quadrants (0° Front, 90° Right, 180° Back, 270° Left).
- A new pure computer vision module (`cv/reference.py`) computes ORB feature matching, homography perspective alignment, and Structural Similarity (SSIM) difference analysis. Newly developed cracks and dents are isolated while pre-existing paint seams, weld lines, and vehicle decals are ignored.
- In `apps/web`, the inspection workflow is enhanced with rocket profile selection, 4-angle upload tabs with camera alignment HUD, an interactive side-by-side comparison slider, and restrained aerospace mission-control styling (Framer Motion transitions, telemetry counters, sleek micro-slat cards) strictly passing all existing constitution gates and design lints.

---

## 2. Technical Context & Monorepo Architecture

- **Backend**: Python 3.11, FastAPI, OpenCV (`opencv-python`), SQLAlchemy 2 (async SQLite).
- **Rule Engine**: Isolated deterministic verdict computation in `rule_engine/verdict.py` (Rule Engine imports nothing from CV or agent).
- **Frontend**: Next.js 15 (Turbopack, App Router), React 19, TypeScript strict (no `any`), Tailwind CSS v4, Motion (`motion`), shadcn/ui.
- **Contract**: `packages/contract` generated from `apps/api/app/openapi.py` via `@hey-api/openapi-ts`. Zero hand-written types in `apps/web`.
- **Atmosphere Constraints**: Strict zero-emoji policy, no colored gradients/glow (verified by `design-lint.test.ts`), no React Bits on decision-critical components (`react-bits-boundary.test.tsx`).

```text
apps/web/
  app/
    inspect/page.tsx               [MODIFY] Rocket profile selector + 4-quadrant uploader
    report/[runId]/page.tsx        [MODIFY] Side-by-side comparison slider & diff overlay
  components/
    inspection/
      MultiAngleUploader.tsx       [NEW] 4-quadrant image dropzone / webcam capture
      CameraGuideHUD.tsx           [NEW] Rocket alignment silhouette stencil
      ComparisonSlider.tsx         [NEW] Interactive baseline vs current wipe slider
      RocketProfileDialog.tsx      [NEW] Modal to register rocket & baseline photos
    react-bits/
      DecryptedText.tsx            [NEW] Aerospace telemetry text reveal (atmosphere only)
      MicroSlats.tsx               [NEW] Segmented mission-control metric bars
apps/api/
  cv/
    reference.py                   [NEW] Homography alignment + SSIM difference detector
  db/
    models.py                      [MODIFY] Add RocketModel and RocketReferenceModel
    repo.py                        [MODIFY] CRUD for rockets and reference images
  app/
    routers/
      rockets.py                   [NEW] Endpoints for rocket registration & baseline images
      inspections.py               [MODIFY] Multi-angle upload support and reference link
  tests/
    unit/
      test_cv_reference.py         [NEW] Pytest for alignment, SSIM, and fail-safe handling
packages/contract/                 [GENERATE] Regenerated types from updated OpenAPI spec
```

---

## 3. Data Model Additions

### SQLite Tables (SQLAlchemy 2 Async)

```sql
CREATE TABLE rockets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    vehicle_class TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rocket_references (
    id TEXT PRIMARY KEY,
    rocket_id TEXT NOT NULL REFERENCES rockets(id) ON DELETE CASCADE,
    quadrant TEXT NOT NULL, -- 'front', 'right', 'back', 'left'
    image_path TEXT NOT NULL,
    keypoint_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rocket_quadrant UNIQUE (rocket_id, quadrant)
);
```

### Extended `runs` Table Link
`runs.rocket_id` (optional foreign key) associates an inspection run with a registered vehicle profile, triggering reference comparison during inspection.

---

## 4. Computer Vision Design (`apps/api/cv/reference.py`)

Per Constitution 3.III, the reference comparison function is pure:
`(reference_bgr: np.ndarray, current_bgr: np.ndarray, quadrant: str) -> Finding`

### Processing Pipeline
1. **Grayscale & Downsample**: Normalize dimensions to matching scale.
2. **Feature Detection**: ORB detector (`nfeatures=1500`) extracts keypoints and descriptors.
3. **Descriptor Matching**: FLANN / Brute-Force Hamming matcher with Lowe's ratio test (0.75).
4. **Homography Warping**: `cv2.findHomography(RANSAC)` aligns the current frame to reference coordinates.
   - *Fail-Safe Check*: If good inliers < 12 or perspective determinant is distorted (> 25° skew), emit degraded `warning` (`reference.alignment_failed`) with `confidence=0.0`. Never yield `ok`.
5. **SSIM Difference Mapping**: Compute Structural Similarity Index map between warped current image and reference.
6. **Morphological Filtering & Contours**: Apply Gaussian blur, Otsu thresholding, and morphological open/close to isolate genuine defect clusters from sensor noise.
7. **Finding Generation**:
   - Metric `deviation_area_pct` = (anomalous pixel area / rocket mask area) * 100.
   - If `deviation_area_pct > 2.0%`: Severity `critical`, hedged message: *"Surface appears to exhibit 2.4% structural deviation against baseline reference."*
   - If `0.4% <= deviation_area_pct <= 2.0%`: Severity `warning`.
   - If `deviation_area_pct < 0.4%`: Severity `ok`.
   - Overlay: Box/polygon contours enclosing anomalous delta regions.

---

## 5. Frontend & UI Architecture

### 1. Aerospace Visual Hierarchy & Atmosphere
- **Telemetry Bars & Counters**: Restrained numeric stats utilizing `CountUp` and `MicroSlats` for mission statistics (e.g., "4/4 Quadrants Aligned", "0.08% Tolerance").
- **Zero Emojis**: All icons come from `lucide-react` (e.g. `Target`, `Compass`, `Crosshair`, `Layers`, `ShieldCheck`).
- **Dark Mission-Control Theme**: High contrast dark zinc (`bg-zinc-950`, `border-zinc-800`), monospaced data fonts (`font-mono`), subtle scan-line borders.
- **Strict Boundary**: No React Bits or decorative motion on `VerdictBadge`, `SeverityIndicator`, `FindingList`, or `Disclaimer`.

### 2. Multi-Angle Uploader & HUD Alignment Guide
- Quadrant Tabs: `[0° FRONT]` `[90° RIGHT]` `[180° BACK]` `[270° LEFT]`.
- Live Webcam HUD Stencil: Canvas/SVG overlay with rocket fuselage silhouette helping operators maintain standard distance and orientation during capture.

### 3. Comparison Slider Component
- Interactive split wiper comparing `Golden Reference` (left) vs `Current Inspection` (right).
- Difference toggle button highlighting detected anomaly contours in high-contrast red vector lines.

---

## 6. Implementation Phases (5-Day Schedule)

### Day 1: Rocket Profile Entities, Database & API
- Create `RocketModel` and `RocketReferenceModel` in `db/models.py`.
- Add repository CRUD methods in `db/repo.py`.
- Create `app/routers/rockets.py` for profile creation, reference image uploads, and list endpoints.
- Export OpenAPI schema and regenerate `@launchguard/contract`.
- Add backend unit tests in `tests/contract/test_rockets.py`.

### Day 2: Multi-Angle Inspection Pipeline & Aggregator
- Update `CreateRunPayload` and inspection router to accept `rocket_id` and 4-quadrant image references.
- Update LangGraph agent state to manage multi-angle findings.
- Ensure deterministic rule engine evaluates aggregated findings from all quadrants (any quadrant `critical` -> overall `NO-GO`).
- Add tests verifying 4-angle findings ingestion and fail-safe handling.

### Day 3: CV Reference Alignment & SSIM Module
- Implement `apps/api/cv/reference.py` with ORB homography alignment and SSIM difference detection.
- Add unit tests in `apps/api/tests/unit/test_cv_reference.py` covering:
  - Identical images -> `ok` (0% deviation).
  - Image with new simulated crack -> `critical` finding with bounding overlay.
  - Image with decal existing in both reference and current -> `ok` (decal ignored).
  - Severely misaligned image -> fail-safe `warning` (degraded).

### Day 4: UI Components & Comparison Experience
- Build `RocketProfileDialog.tsx` in `apps/web/components/inspection/` for profile management.
- Build `MultiAngleUploader.tsx` with 4-quadrant tabs and `CameraGuideHUD.tsx` alignment stencil.
- Build `ComparisonSlider.tsx` for side-by-side baseline vs current inspection verification.
- Integrate into `/inspect` and `/report/[runId]` pages.
- Add atmospheric telemetry enhancements (`MicroSlats`, `DecryptedText`, smooth Motion transitions).

### Day 5: Verification, Design-Lint & Demo Fixtures
- Generate test fixtures: `rocket_golden_reference.jpg`, `rocket_current_intact.jpg`, `rocket_current_cracked.jpg`.
- Run full verification suite:
  - `pnpm --filter @launchguard/web typecheck`
  - `pnpm --filter @launchguard/web lint`
  - `pnpm --filter @launchguard/web test --run`
  - `pytest` across all backend test modules.
- Update documentation and pitch materials with reference inspection capabilities.
