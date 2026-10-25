# Feature Specification: Golden Reference & Multi-Angle Rocket Inspection

**Feature Branch**: `002-reference-inspection`  
**Created**: 2026-10-06  
**Status**: Draft  
**Parent Specification**: `specs/001-launchguard-mvp/spec.md`  
**Governing Document**: `.specify/memory/constitution.md` (v1.0.0)

---

## 1. Executive Summary & Problem

In current pre-launch inspections, evaluating a rocket from a single camera perspective leaves up to 75% of the cylindrical fuselage uninspected. Furthermore, generic crack/defect detection models struggle with vehicle-specific surface variations: manufacturing seams, painted livery, sponsor decals, and welded joints can either trigger false alarms or camouflage genuine micro-fissures and transport damage.

Aerospace quality assurance in industrial space programs relies on **reference-based anomaly verification (golden sample comparison)**: matching a field inspection against the vehicle's pristine baseline ("as-built" state).

Feature `002-reference-inspection` elevates LaunchGuard AI to this standard:
1. **Rocket Profiles & Baseline Enrollment**: Operators register specific vehicles and record 4-quadrant Golden Reference images (0° Front, 90° Right, 180° Back, 270° Left) taken in factory-certified condition.
2. **Multi-Angle Inspection Runs**: Operators upload or stream 4-angle field captures in a single evaluation run.
3. **Reference Comparison Computer Vision**: Server-side OpenCV feature alignment (ORB homography) and Structural Similarity (SSIM) difference analysis isolate new structural anomalies while ignoring pre-existing livery and weld lines.
4. **Deterministic Rule Engine Integration**: Reference anomalies produce structured findings (`reference.deviation`) with measured altered pixel area and deviation severity. The rule engine preserves its non-negotiable deterministic boundary: rules decide the verdict, the LLM only explains.
5. **Interactive Mission-Control UI**: A professional side-by-side comparison slider, difference heatmaps, camera alignment stencil HUD, and restrained GSAP / Motion telemetry atmosphere strictly conforming to the project's zero-emoji, no-gradient, dark-mode constitution.

---

## 2. User Scenarios & Requirements

### User Story 1 — Rocket Profiles & Golden Reference Enrollment (Priority: P1)
As a launch engineer, I want to register a rocket vehicle profile (e.g. "Aero-X Mk IV") and store 4 pristine reference photographs (Front, Right, Back, Left), so that subsequent inspections have an immutable baseline to compare against.

**Acceptance Criteria**:
1. Operators can create a rocket profile with name, vehicle class, and notes.
2. The enrollment interface allows uploading or capturing 4 designated quadrant images (0° Front, 90° Right, 180° Back, 270° Left).
3. The server validates image dimensions (minimum 640x480, maximum 10MB) and stores reference metadata in SQLite.
4. Existing rocket profiles can be viewed, listed, and selected during pre-launch inspection setup.

### User Story 2 — Multi-Angle Inspection Run (Priority: P1)
As a launch engineer on the pad, I want to upload 4 photos covering all four quadrants of the vehicle in a single inspection run, so that 100% of the rocket's exterior circumference is checked before rollout.

**Acceptance Criteria**:
1. Pre-launch inspection upload form supports selecting a registered rocket profile and providing 4 images mapped to the 4 quadrants (Front, Right, Back, Left).
2. The inspection timeline expands each quadrant as a sub-phase or executes 4-angle CV checks per step.
3. Findings from all 4 angles are collected into the run's findings log.
4. If any single angle exhibits a `critical` defect (e.g. 4mm structural crack on the Back angle), the overall run verdict deterministically results in `NO-GO`.
5. If an angle photo is missing or fails alignment, the module reports `warning` (Fail-Safe Principle II) and cannot return `ok`.

### User Story 3 — Reference Alignment & SSIM Anomaly Detection (Priority: P1)
As an inspection engineer, I want the system to align the current inspection photo against the golden reference and calculate structural deviations, so that newly developed cracks and dents are detected regardless of complex surface decals.

**Acceptance Criteria**:
1. All CV execution occurs in `apps/api/cv/reference.py` using Python OpenCV only (Constitution 3.II).
2. The module detects keypoints and computes homography transformation between reference and current frames to correct minor camera angle shifts (up to 15° rotation / scale shift).
3. The module computes Structural Similarity Index (SSIM) difference maps and morphological contours of altered regions.
4. Altered regions exceeding the noise threshold are emitted as structured findings:
   - Module: `cv.reference`
   - Check ID: `reference.structural_deviation`
   - Severity: `warning` (deviation area between 0.5% and 2.0% of bounding box) or `critical` (deviation area > 2.0% or significant high-gradient discontinuity)
   - Overlay: Polygon/box contours enclosing the detected anomalous difference.
   - Metrics: `deviation_area_pct`, `ssim_score`.
5. Hedged language ("appears to show structural deviation", "possible surface anomaly") is strictly enforced in finding messages.

### User Story 4 — Side-by-Side Comparison UI & HUD Guide (Priority: P2)
As a range safety officer, I want an interactive visual slider comparing the golden reference against the current inspection image with toggled difference contours, and a camera HUD guide for field operators.

**Acceptance Criteria**:
1. The inspection report and live inspect views provide a split comparison slider allowing operators to wipe between "Baseline Reference" and "Current Inspection".
2. An overlay toggle enables/disables the red-line difference contour bounding boxes.
3. The webcam capture tool displays an optional lightweight alignment stencil/HUD outline helping the operator position the vehicle within the frame.
4. The mandatory range safety disclaimer *"Decision-support tool. Not a replacement for certified range safety."* is clearly visible.

### User Story 5 — Restrained Mission-Control UI Polish (Priority: P2)
As a mission-control operator, I want a crisp, responsive, high-density aerospace dashboard that looks like real flight software, avoiding flashy animations or generic AI styling.

**Acceptance Criteria**:
1. UI maintains strict zero-emoji policy across all components, labels, and text.
2. Styling strictly complies with dark mission-control palette without colored gradients, neon glow, or colored shadows (passing `design-lint.test.ts`).
3. Motion enhancements use Framer Motion / Motion primitives and allowed React Bits (`CountUp`, `SpotlightCard`, `AnimatedList`, `DecryptedText`) only for atmosphere (header statistics, telemetry counters, subtle quadrant tabs).
4. No React Bits or decorative animations are applied to decision-critical components (`VerdictBadge`, `SeverityIndicator`, `FindingList`, `Disclaimer`), fully satisfying `react-bits-boundary.test.tsx` and Constitution 4.III.

### User Story 6 — Test Suite & Demo Scenarios (Priority: P1)
As a developer and hackathon presenter, I need automated test coverage and reproducible demo fixtures demonstrating reference-based detection.

**Acceptance Criteria**:
1. Unit tests in `apps/api/tests/unit/test_cv_reference.py` verifying alignment, fail-safe degradation on misaligned frames, and deterministic findings generation.
2. Web tests in `apps/web/tests/` verifying multi-angle upload state, comparison slider interactions, and design-lint compliance.
3. Demo fixture set (`rocket_reference_front.jpg`, `rocket_current_damaged.jpg`) containing an intentional decal and a newly introduced crack, proving the reference comparison detects the crack while ignoring the decal.

---

## 3. Constitution & Architecture Alignment

| Constitution Principle | How Feature 002 Complies |
|---|---|
| **2.I Deterministic Decisions** | Reference comparison computes numeric deviation metrics; the rule engine alone determines whether deviation metrics trigger `warning` or `critical` and assigns the verdict. |
| **2.II Fail Safe** | If camera perspective is too misaligned (> 25° homography skew) or feature matching fails (< 10 good keypoint matches), the module returns `warning` with degraded flag; it never silently yields `ok`. |
| **2.III Explainable Findings** | Every reference finding includes overlay coordinates, exact `deviation_area_pct`, `ssim_score`, and human-readable hedged explanation. |
| **2.IV Honest Uncertainty** | Messages use hedged language ("appears to show structural deviation"); disclaimer is permanently anchored. |
| **3.I Two Deployables, One Contract** | New endpoints (`POST /api/rockets`, `POST /api/rockets/{id}/references`, multi-angle runs) exported via OpenAPI and compiled into `@launchguard/contract`. |
| **3.II CV Lives in Python Only** | Image alignment, SSIM, and contour detection run entirely in `apps/api/cv/reference.py` using Python OpenCV; zero browser-side CV. |
| **4.III Atmosphere Without Compromise** | UI motion is restricted to telemetry counters, layout transitions, and card atmospheres; zero motion on the verdict badge, severity indicators, finding lists, or disclaimer. |
