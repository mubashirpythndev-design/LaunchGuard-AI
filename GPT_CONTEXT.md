# LaunchGuard AI: Master Engineering & Context Handoff

> Comprehensive context document and system prompt for continuing development of LaunchGuard AI with any LLM (e.g., ChatGPT / GPT-4 / o1).

---

## 1. System Prompt to Paste into GPT

Copy and paste the following block into GPT at the beginning of your session:

```markdown
You are an expert full-stack aerospace AI engineer pair-programming on "LaunchGuard AI".
You must read and strictly follow the architecture, non-negotiable safety rules, and current state documented below.

### Absolute Governing Rules (Non-Negotiables):
1. Deterministic Verdicts: The GO / HOLD / NO-GO verdict is calculated EXCLUSIVELY by apps/api/rule_engine/verdict.py. The rule engine imports nothing from cv/ or agent/. The LLM explains findings and recommends actions; it MUST NEVER alter or upgrade a verdict.
2. Fail-Safe: Any module that errors, times out, or scores below MIN_CONFIDENCE_FOR_OK (0.35) yields "warning" with degraded=True, NEVER "ok".
3. CV in Python Only: All computer vision algorithms (OpenCV, YOLOv8) run exclusively in apps/api/cv/. OpenCV.js or browser-side detection is prohibited.
4. Two Deployables, One Contract: apps/web declares no API types of its own. packages/contract is auto-generated from FastAPI's OpenAPI document via `pnpm generate`. Never hand-edit packages/contract/src/.
5. Atmosphere Without Compromise: Interactive motion is for atmosphere only. Never place animations or React Bits on the decision-critical path (VerdictBadge, SeverityIndicator, FindingList, Disclaimer).
6. Design Constraints: ZERO EMOJIS anywhere in the code or text. No colored gradients, neon glow, or drop shadows (enforced by design-lint.test.ts). Dark mission-control theme only.
7. Disclaimers: The disclaimer "Decision-support tool. Not a replacement for certified range safety." must remain permanently visible on all views.
8. Type Safety: TypeScript strict (no `any`), Python 3.11 with `mypy --strict`.

Please confirm you understand this system and wait for my next development instruction.
```

---

## 2. Project Architecture & Monorepo Structure

```text
D:\Works\hackathon KYS\
├── apps/
│   ├── api/                     # Python 3.11 + FastAPI + OpenCV + YOLOv8 + LangGraph + SQLite
│   │   ├── agent/               # LangGraph state machine, orchestrator, narrative generator
│   │   ├── app/                 # FastAPI routes (config, demo, health, inspections, monitor, rockets, runs, share)
│   │   ├── cv/                  # Pure computer vision functions (body, fins, cues, zone, frameio, failsafe)
│   │   ├── db/                  # SQLAlchemy 2 async SQLite models and repository functions
│   │   ├── rule_engine/         # Isolated deterministic decision engine (imports NO CV, NO LLM)
│   │   ├── tests/               # Pytest suite (93 automated tests)
│   │   └── yolov8n.pt           # YOLOv8 nano model weights
│   └── web/                     # Next.js 15 (App Router, Turbopack, React 19, Tailwind CSS v4, Motion)
│       ├── app/                 # App Router pages (/inspect, /monitor, /report/[runId], /history, /share/[token])
│       ├── components/          # shadcn/ui primitives, inspection viewers, zone editor, verdict components
│       ├── hooks/               # useRunStream (SSE streaming), useWebcam
│       ├── stores/              # Zustand stores (e.g., zone editor store)
│       └── tests/               # Vitest suite (49 automated tests, including design-lint and a11y)
├── packages/
│   └── contract/                # Generated TypeScript types and Zod schemas from FastAPI OpenAPI
├── specs/
│   ├── 001-launchguard-mvp/     # MVP specifications, contracts, and tasks
│   └── 002-reference-inspection/# Golden reference and multi-angle inspection specifications
└── scripts/
    └── export_openapi.py        # OpenAPI JSON exporter script
```

---

## 3. Technology Stack & Key Commands

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2 (aiosqlite), OpenCV (`opencv-python`), Ultralytics YOLOv8n, LangGraph with `AsyncSqliteSaver`, OpenAI SDK (`gpt-4o-mini`).
- **Frontend**: Next.js 15, React 19, TypeScript 5, Tailwind CSS v4, Motion (`motion`), Radix UI / shadcn/ui.
- **Contract Generator**: `@hey-api/openapi-ts`.

### Verification Commands:
```bash
# Backend verification (from apps/api):
.\.venv\Scripts\pytest -q
.\.venv\Scripts\mypy --strict app cv agent rule_engine db
.\.venv\Scripts\ruff check .

# Frontend verification (from repo root):
pnpm --filter @launchguard/web typecheck
pnpm --filter @launchguard/web lint
pnpm --filter @launchguard/web test --run

# Contract code generation:
.\apps\api\.venv\Scripts\python.exe scripts/export_openapi.py
pnpm --filter @launchguard/contract generate
```

---

## 4. Current Status: What Has Been Built

### Completed in 001-launchguard-mvp:
1. **Pre-Launch Inspection**: Image upload inspecting body cracks, dents, fin symmetry, and launchpad clearance.
2. **Launchpad Monitor**: Live stream / video / webcam monitoring for danger exclusion zone breaches, smoke, fire, and liquid propellant cues.
3. **Deterministic Rule Engine**: Pure mathematical evaluation mapping findings and manual inputs (wind, visibility, precipitation) to `GO / HOLD / NO-GO`.
4. **Agentic SSE Streaming**: LangGraph streaming execution steps (`run.started`, `checklist.step.started`, `finding.raised`, `checklist.step.finished`, `run.completed`).
5. **Human-in-the-Loop Interrupt**: Pauses when weather manual inputs are required, then resumes upon submission.
6. **AI Safety Officer Narrative**: `gpt-4o-mini` synthesizes executive summary; falls back cleanly to template if LLM is offline or times out (verdict unaffected).
7. **Public Shared Reports**: Cryptographic read-only share token `/share/[token]`.

### Completed in 002-reference-inspection (Day 1):
1. **Database Models**:
   - `RocketModel`: Vehicle profile (`id`, `name`, `vehicle_class`, `notes`, `created_at`).
   - `RocketReferenceModel`: Baseline golden reference photos per quadrant (`front`, `right`, `back`, `left`) with unique constraint on `(rocket_id, quadrant)`.
2. **Repository Layer**: CRUD operations in `apps/api/db/repo.py` (`create_rocket`, `get_rocket`, `list_rockets`, `upsert_rocket_reference`, etc.).
3. **API Router**: `apps/api/app/routers/rockets.py` for registering rockets, uploading baseline images (validates format, extracts ORB keypoints, saves to `data/references/`), and serving binary baseline files.
4. **Contract Generated**: All types synchronized with `packages/contract`.
5. **All Tests Passing**: 93 backend pytest tests and 49 frontend Vitest tests pass with 0 errors.

---

## 5. Next Implementation Tasks (Day 2 to Day 5)

### Day 2 (Current Next Step): Multi-Angle Inspection Pipeline & Aggregator
- Extend `POST /api/inspections` and `CreateRunPayload` to accept `rocket_id` and 4 quadrant images (Front 0°, Right 90°, Back 180°, Left 270°).
- Update LangGraph inspection graph to iterate through all 4 quadrants and aggregate findings into a single run.
- Ensure the deterministic rule engine evaluates aggregated findings (any quadrant `critical` -> overall `NO-GO`).

### Day 3: CV Reference Alignment & SSIM Module
- Implement `apps/api/cv/reference.py`:
  - `align_and_compare_reference(reference_bgr, current_bgr, quadrant) -> Finding`
  - ORB keypoint matching + homography perspective warping (max 15° skew).
  - Structural Similarity Index (SSIM) difference mapping + contour extraction.
  - Fail-safe check: Skew > 25° or < 12 inliers yields `warning` (degraded).
  - Emits `reference.structural_deviation` finding with measured `deviation_area_pct` and `ssim_score`.

### Day 4: UI Interactive Comparison & HUD
- Build `MultiAngleUploader.tsx`: 4-quadrant tabs with camera alignment HUD stencil (`CameraGuideHUD.tsx`).
- Build `ComparisonSlider.tsx`: Interactive wipe slider in report view comparing Baseline Reference vs Current Inspection with red anomaly contours.
- Build `RocketProfileDialog.tsx`: Modal dialog to register vehicles and upload baseline photos.

### Day 5: Verification & Demo Scenarios
- End-to-end automated tests.
- Demo fixtures (`rocket_reference.jpg`, `rocket_current_cracked.jpg`) proving decal invariance and micro-crack detection.
