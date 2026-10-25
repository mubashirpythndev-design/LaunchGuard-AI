# Tasks: LaunchGuard AI MVP

**Input**: Design documents from `specs/001-launchguard-mvp/`
**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`
**Constitution**: `.specify/memory/constitution.md` (v1.0.0) — every task MUST comply. If a task
cannot comply, resolve the conflict in `spec.md` or `plan.md` first; do not weaken the task.
**Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Spec**: [spec.md](./spec.md)

**Tests**: **REQUIRED, not optional** (Constitution 5.II — Test Obligations). Every CV module
needs a fixture test with at least one **passing** and one **failing** image. Every demo scenario
(GO, HOLD, NO-GO) needs a Playwright spec. Web code touched by a story needs Vitest + React
Testing Library. API code touched by a story needs Pytest.

**Story priority order** is taken from `spec.md`, not from the order the stories were written.
Delivery order is **US1 (P1) → US2 (P2) → US4 (P3) → US6 (P4) → US5 (P5) → US3 (P6)**.

Three deviations from the supplied task outline are marked **[CHANGED]** at the task, with the
reason inline. All three are Constitution MUSTs, and all three are recorded in
[plan.md](./plan.md) §Complexity Tracking and in [research.md](./research.md):

| Outline said | Plan mandates | Why |
|---|---|---|
| `agent/rules.py` computes the verdict | `rule_engine/verdict.py`, importing nothing from `cv/` or `agent/` | Constitution 2.I — the verdict module must not be able to reach a model (R6) |
| Verdict revealed with `DecryptedText` | Static text + icon + colour; React Bits never on the verdict badge | Constitution 4.III and UX-003 (R3) |
| `openapi-typescript` for types **and Zod** | `@hey-api/openapi-ts` with the Zod v4 plugin | `openapi-typescript` emits types only, so Zod schemas would be hand-written — the exact drift Constitution 3.I forbids (R1) |

The outline's 8-hour hour-by-hour shape is mapped onto this file's task IDs in
[Hackathon 8-Hour Order](#hackathon-8-hour-order) as the scheduling view. It is not the
dependency order — several of its entries can only start after a later phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: `US1`–`US6`, mapping to `spec.md` user stories. Setup, Foundational, and Polish
  phases carry no story label.
- Every description names an exact file path.

## Path Conventions

Constitution 3.I (Two Deployables, One Contract) fixes the layout. These paths are mandatory;
do not invent a single-project, generic `frontend/` + `backend/`, or mobile structure.

- **Web**: `apps/web/app/`, `apps/web/components/ui/`, `apps/web/components/react-bits/`,
  `apps/web/components/verdict/`, `apps/web/components/inspection/`, `apps/web/components/monitor/`,
  `apps/web/components/report/`, `apps/web/components/demo/`, `apps/web/lib/`, `apps/web/stores/`,
  `apps/web/hooks/`, `apps/web/tests/`
- **API**: `apps/api/app/`, `apps/api/app/routers/`, `apps/api/agent/`, `apps/api/cv/`,
  `apps/api/rule_engine/`, `apps/api/db/`, `apps/api/tests/{unit,contract,e2e,fixtures/images}/`
- **Contract**: `packages/contract/openapi.json`, `packages/contract/openapi-ts.config.ts`,
  `packages/contract/src/` — **generated only**; never hand-write or hand-edit these files
- **E2E**: `e2e/` — one Playwright spec per demo scenario
- **Scripts**: `scripts/` — `export_openapi.py` at the root, not under `apps/api/`
- **Docs**: `specs/001-launchguard-mvp/`

Dependency direction is one-way: `apps/api/cv/` → `apps/api/rule_engine/` ← `apps/api/agent/`.
`apps/api/rule_engine/` imports nothing from `cv/` or `agent/` (Constitution 2.I, enforced by T020
and T046).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, tooling, and the fixture set. No story label.

- [x] T001 Create the pnpm workspace root: `pnpm-workspace.yaml` listing `apps/*` and `packages/*`, root `package.json` with `generate` and `prebuild` scripts, `.npmrc`, and `.gitignore` covering `packages/contract/src/`, `node_modules/`, `.venv/`, `*.db`, `media/`
- [x] T002 [P] Scaffold `apps/web` with `create-next-app` (TypeScript, App Router, Tailwind v4, ESLint, no `src/` dir), confirm `strict: true` in `apps/web/tsconfig.json`, add the `@/*` path alias, and add Prettier with `apps/web/.prettierrc`
- [x] T003 [P] Create `apps/api` package layout — `apps/api/{app,agent,cv,rule_engine,db,tests}/` — with `apps/api/pyproject.toml` pinning fastapi, uvicorn, pydantic, pydantic-settings, opencv-python-headless, numpy, ultralytics, sqlalchemy, aiosqlite, langgraph, langgraph-checkpoint-sqlite, openai, python-multipart, pytest, ruff, mypy; add `GET /api/health` in `apps/api/app/routers/health.py`
- [x] T004 [P] Create `packages/contract/package.json` with a `generate` script and `packages/contract/openapi-ts.config.ts` using `@hey-api/openapi-ts` with plugins `['@hey-api/typescript', { name: 'zod', compatibilityVersion: 4, types: { infer: true } }]`
- [x] T005 [P] Write `scripts/export_openapi.py` that imports the FastAPI app from `apps/api/app/main.py` and writes `app.openapi()` to `packages/contract/openapi.json` without starting a server
- [x] T006 [P] Create `.env.example` at the repo root plus `apps/api/.env.example` listing `OPENAI_API_KEY`, `OPENAI_MODEL`, `DATABASE_URL`, `CHECKPOINT_DB`, `MEDIA_ROOT`, `CORS_ORIGINS`, `LOG_LEVEL`, `OPENAI_TIMEOUT_S`; add `apps/api/.env` and `apps/web/.env*` to `.gitignore`
- [x] T007 [P] Configure `apps/api/pyproject.toml` for Ruff and `mypy --strict` over `app`, `cv`, `agent`, `rule_engine`, `db`
- [x] T008 [P] Run `pnpm dlx shadcn@latest init` in `apps/web`, then add components into `apps/web/components/ui/`: button, card, badge, tabs, dialog, sheet, input, label, select, switch, checkbox, progress, skeleton, separator, table, tooltip, sonner, alert, scroll-area, dropdown-menu, chart, toggle-group, resizable
- [x] T009 [P] Add `apps/web` dependencies: `@tanstack/react-query`, `zod`, `react-hook-form`, `@hookform/resolvers`, `zustand`, `motion`, `lucide-react`
- [x] T010 [P] Install atmosphere-only React Bits into `apps/web/components/react-bits/` from the `@react-bits` registry as `TS-TW` variants — `Aurora`, `Threads`, `CountUp`, `SpotlightCard`, `ShinyText`, `GradientText` — and verify each compiles under `strict: true`. **Do not install `DecryptedText`, `ClickSpark`, or any Pro component**; Pro is a separate license-gated registry
- [x] T011 Add the three demo fixture images `normal.jpg`, `fin_misaligned.jpg`, `person_in_zone.jpg` to `apps/web/public/demo/` and `apps/api/tests/fixtures/images/`, and copy the demo trio to `apps/api/tests/fixtures/images/{check_id}__pass` / `__fail` names per research R14. Record provenance in `apps/api/tests/fixtures/images/SOURCES.md`
- [x] T012 [P] Create `apps/api/tests/conftest.py` with `FIXTURES_IMAGES` path constant, a temporary-SQLite `db_session` fixture, and a `no_network` fixture that blocks outbound sockets for the rule-engine and offline-demo tests
- [x] T013 [P] Configure GitHub Actions in `.github/workflows/ci.yml` running Ruff, `mypy --strict`, ESLint, `pnpm typecheck`, Pytest, Vitest, Playwright, plus a contract-drift step that runs `pnpm generate` then `git diff --exit-code packages/contract`

**Checkpoint**: Workspace builds, `GET /api/health` responds, `pnpm generate` produces a
`packages/contract/src/` directory, and CI is green on an empty feature branch.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The decision path, the contract, and the streaming substrate. **No user story work
can begin until this phase is complete.** No story label.

### Decision path — the rule engine

- [x] T014 [P] Create `apps/api/rule_engine/types.py` with frozen dataclasses `Severity`, `Verdict`, `Measurement`, `Overlay`, `Finding`, `Thresholds`, `ManualInputSet`, `StepResult`, `Decision`, plus `validate_finding()` raising `InadmissibleFinding` when a required field is missing (Constitution 2.III) and `is_threshold_ambiguous()`
- [x] T015 [P] Create `apps/api/rule_engine/config.py` with `MIN_CONFIDENCE_FOR_OK = 0.35`, the one-way `apply_confidence_floor()` that promotes `ok` to `warning` and never downgrades, the `Thresholds` defaults from `spec.md` Assumption 6, and the risk capacities `WARNING_CAPACITY = 2.0` / `CRITICAL_CAPACITY = 3.0`
- [x] T016 [P] Create `apps/api/rule_engine/registry.py` with the 15 stable check ids mapped to the 5 ordered steps (`body`, `fins`, `launchpad_area`, `weather_manual`, `decision`) and the labels used in the report
- [x] T017 Create `apps/api/rule_engine/verdict.py` implementing the three-rule order — any `critical` → `NO-GO`; else any `warning` or missing mandatory input → `HOLD`; else `GO` — returning `Decision` with ordered `reasons` and rule-derived `recommended_actions`
- [x] T018 Create `apps/api/rule_engine/risk.py` implementing the banded saturating score (GO 0–30, HOLD 40–69, NO-GO 70–100) with the `warning_evidence`, `critical_evidence`, and `low_confidence` accumulators
- [x] T019 Create `apps/api/rule_engine/manual.py` evaluating wind > 10 / > 15 m/s, poor visibility, heavy precipitation, and area-not-cleared, using the configured thresholds, and naming every absent mandatory input
- [x] T020 Create `apps/api/rule_engine/__init__.py` exporting the engine surface, and add a repo-level import guard test that fails if `rule_engine` imports anything from `cv` or `agent`

### Persistence

- [x] T021 [P] Create `apps/api/db/base.py` with the SQLAlchemy 2 engine, `async_sessionmaker`, and the `DATABASE_URL` default
- [x] T022 Create `apps/api/db/models.py` with all 8 tables — `runs`, `findings`, `danger_zones`, `checklist_steps`, `manual_inputs`, `run_events`, `reports`, `demo_scenarios` — including the `confidence BETWEEN 0.0 AND 1.0` check constraint and the unique constraints on `(run_id, position)` and `(run_id, seq)`
- [x] T023 Create `apps/api/db/repo.py` with data-access functions only: run create/update, finding append, zone upsert/delete, manual-input upsert, event append with monotonic `seq`, report upsert, demo-scenario read
- [x] T024 [P] Create `apps/api/db/__init__.py` and wire table creation into the FastAPI lifespan in `apps/api/app/main.py`

### Streaming substrate

- [x] T025 Create `apps/api/app/events.py` — an in-process `asyncio` pub/sub keyed by `run_id` that **persists every event to `run_events` before publishing it**, assigns the monotonic `seq`, supports `Last-Event-ID` replay from the database, emits a `:heartbeat` comment every 15 s, and unsubscribes on disconnect
- [x] T026 Create `apps/api/app/main.py` with the app factory, CORS, and the lifespan hook that opens `AsyncSqliteSaver.from_conn_string(settings.checkpoint_db)` and **closes it on shutdown** (an unclosed checkpoint connection makes the graph appear to hang), and that reconciles runs left `running` per research R12
- [x] T027 [P] Create `apps/api/app/config.py` reading settings via `pydantic-settings`, exposing `MIN_CONFIDENCE_FOR_OK` and the thresholds through `GET /api/config` together with the mandated disclaimer string
- [x] T028 Create `apps/api/app/openapi.py` assembling the OpenAPI document, with response models on every route so the generated contract is complete rather than `any`-shaped

### Web foundations

- [x] T029 Run `pnpm generate` to produce `packages/contract/src/` (TypeScript types + Zod v4 schemas) from `apps/api`
- [x] T030 Create `apps/web/lib/schemas.ts` as **re-exports only** from `@launchguard/contract` — zero type declarations, zero hand-written API types (Constitution 3.I)
- [x] T031 [P] Create `apps/web/lib/api-client.ts` wrapping the generated SDK with the base URL and the typed error envelope
- [x] T032 [P] Create `apps/web/lib/sse.ts` — a typed `EventSource` wrapper that sends `Last-Event-ID` on reconnect, re-dispatches `Last-Event-ID` from the previous connection, and exposes a reducer-friendly event union
- [x] T033 [P] Create `apps/web/lib/hedged.ts` as the single source of hedged user-facing copy, exporting `hedged()` and the banned certainty-word and certification-claim lists
- [x] T034 Create `apps/web/app/api/[...path]/route.ts` — the SSE-safe proxy with `runtime = 'nodejs'`, `dynamic = 'force-dynamic'`, `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`, upstream `Content-Length` stripped, and teardown on `req.signal`
- [x] T035 [P] Create `apps/web/app/providers.tsx` mounting the TanStack Query client, the shadcn `Toaster`, and the `MotionSafe` boundary
- [x] T036 [P] Create `apps/web/components/verdict/VerdictBadge.tsx` rendering verdict as **text + icon + colour**, static, with no React Bits and no motion
- [x] T037 [P] Create `apps/web/components/verdict/Disclaimer.tsx` rendering the exact mandated string, shared by all five screens
- [x] T038 [P] Create `apps/web/components/verdict/SeverityIndicator.tsx` rendering severity as text + icon + colour, legible in black and white
- [x] T039 Create `apps/web/hooks/use-reduced-motion.ts` and `apps/web/components/verdict/MotionSafe.tsx` — when reduced motion is preferred, React Bits are **not mounted at all** rather than mounted with a zero duration
- [x] T040 Create `apps/web/app/globals.css` with the dark mission-control shadcn theme and the `--go` / `--hold` / `--nogo` tokens, plus the print stylesheet that keeps the report legible in black and white

### Foundational tests (REQUIRED by Constitution 5.II)

- [x] T041 [P] Pytest verdict matrix in `apps/api/tests/unit/test_verdict.py` — every combination of `critical` / `warning` / `ok` and present / missing mandatory inputs against the expected verdict, with `no_network` asserted
- [x] T042 [P] Pytest risk bands in `apps/api/tests/unit/test_risk.py` — assert GO ≤ 30, HOLD ∈ 40–69, NO-GO ≥ 70, and that the score is order-independent and never an input to the verdict
- [x] T043 [P] Pytest confidence floor in `apps/api/tests/unit/test_config.py` — `ok` at 0.34 floors to `warning`; `critical` at 0.20 stays `critical`; `apply_confidence_floor` never returns `ok` below 0.35
- [x] T044 [P] Pytest manual rules in `apps/api/tests/unit/test_manual.py` — wind 10.0 / 15.0 boundaries on the less-severe side, poor visibility, heavy precipitation, area-not-cleared, and every absent input named
- [x] T045 [P] Pytest measurement ambiguity in `apps/api/tests/unit/test_ambiguity.py` — a fin angle within 1.5° of a threshold yields a `near_threshold_note`; outside it does not
- [x] T046 [P] Pytest import-isolation guard in `apps/api/tests/unit/test_rule_engine_isolation.py` — assert `rule_engine` imports nothing from `cv` or `agent` by walking the module graph
- [x] T047 [P] Pytest SSE fan-out in `apps/api/tests/unit/test_events.py` — two subscribers both receive every event, `seq` is gapless, and a subscriber reconnecting with `Last-Event-ID` receives no duplicates
- [x] T048 [P] Pytest startup recovery in `apps/api/tests/unit/test_recovery.py` — a run interrupted at a checkpoint becomes `paused`; a crashed run becomes `failed` with `interrupted_by_restart` and never a verdict
- [x] T049 [P] Pytest OpenAPI conformance in `apps/api/tests/contract/test_openapi.py` — every declared route has a response model, and regenerating `packages/contract` produces no diff
- [x] T050 [P] Vitest for the decision-critical components in `apps/web/tests/verdict.test.tsx` — `VerdictBadge` renders text and an icon for each of GO / HOLD / NO-GO, `Disclaimer` renders the exact mandated string, and `SeverityIndicator` never conveys state by colour alone
- [x] T051 [P] Vitest for `MotionSafe` in `apps/web/tests/motion-safe.test.tsx` — with reduced motion preferred, a React Bits child is not rendered

**Checkpoint**: A verdict is computable and testable with no model, no network, and no CV code
importable from the rule engine. This is the gate that makes Constitution 2.I true before a
single detection module exists.

---

## Phase 3: User Story 1 — Pre-Launch Inspection (Priority: P1) 🎯 MVP

**Goal**: An engineer uploads a rocket photo and receives per-module findings with annotation
overlays, severities, confidence, measured metrics, and a verdict — with no language model in the
path.

**Independent Test**: Upload `normal.jpg` and `fin_misaligned.jpg`. Each produces a complete
per-module result set with severities, confidence, and annotations, a verdict, and a risk score.
Assert no outbound network call occurs.

### Tests for User Story 1 (REQUIRED by Constitution 5.II)

- [x] T052 [P] [US1] Pytest fixture test for `cv/body.py` in `apps/api/tests/unit/test_cv_body.py` — a `__pass` and a `__fail` image, asserting cracks, dents, damage, and burn marks
- [x] T053 [P] [US1] Pytest fixture test for `cv/fins.py` in `apps/api/tests/unit/test_cv_fins.py` — `__pass` within 1.5° of known → `ok`; `__fail` → `warning` or `critical`; boundaries at exactly 3° and 6° fall on the less-severe side
- [x] T054 [P] [US1] Pytest fail-safe test in `apps/api/tests/unit/test_failsafe.py` — a module forced to raise and a module forced to time out both yield `severity="warning"` at `confidence=0.0` with `degraded=true`, never `ok`
- [x] T055 [P] [US1] Pytest contract test in `apps/api/tests/contract/test_inspections.py` — `POST /api/inspections` returns `201` with a run handle; oversize, wrong-type, and corrupt uploads each return their specific code and create no run
- [x] T056 [P] [US1] Vitest + RTL for the uploader in `apps/web/tests/uploader.test.tsx` — drag-drop and file-picker both validate type and size, and the preview renders before the request resolves
- [x] T057 [P] [US1] Vitest + RTL for `AnnotatedViewer` in `apps/web/tests/annotated-viewer.test.tsx` — per-module overlay toggles, and normalized coordinates re-render at a different display size
- [x] T058 [US1] Playwright e2e in `e2e/inspection.spec.ts` — upload `fin_misaligned.jpg`, assert a `warning` finding shows the deviation in degrees and the disclaimer is visible

### Implementation for User Story 1

- [x] T059 [P] [US1] Create `apps/api/cv/frameio.py` — decode and validate an image, returning low confidence for uniform, too-dark, or too-bright frames rather than raising
- [x] T060 [P] [US1] Create `apps/api/cv/models.py` — the YOLOv8n lazy singleton holding **weights only**, guarded by a lock, with `predict()` taking a fresh `ndarray` and storing nothing per request
- [x] T061 [US1] Create `apps/api/cv/body.py` as pure `(input) -> list[Finding]` covering cracks, dents, surface damage, and burn marks
- [x] T062 [US1] Create `apps/api/cv/fins.py` as a pure function computing fin angle deviation with `error_margin = 1.5` and an `arc` overlay
- [x] T063 [US1] Create `apps/api/cv/annotate.py` producing normalized `Overlay` JSON and a server-rendered annotated JPEG
- [x] T064 [US1] Create `apps/api/cv/failsafe.py` — the fail-safe decorator wrapping every CV entry point so an exception or timeout becomes `severity="warning"` with a hedged message naming the module
- [x] T065 [US1] Create `apps/api/agent/tools.py` with typed pure tool wrappers — `inspect_body`, `check_fin_alignment`, `check_launchpad_clear` — each returning `list[Finding]`
- [x] T066 [US1] Create `apps/api/app/routers/inspections.py` with `POST /api/inspections` and `GET /api/runs/{run_id}`, validating type, size, and decodability before a run is created
- [x] T067 [US1] Create `apps/api/app/routers/config.py` serving `GET /api/config` with the thresholds, `min_confidence_for_ok`, and the disclaimer
- [x] T068 [US1] Run `pnpm generate` to regenerate `packages/contract` from the updated OpenAPI document
- [x] T069 [US1] Create `apps/web/components/inspection/Uploader.tsx` — a client component with drag-drop, inline validation via React Hook Form + Zod, and an immediate local object-URL preview
- [x] T070 [US1] Create `apps/web/components/inspection/AnnotatedViewer.tsx` drawing normalized overlays as SVG with per-module toggles
- [x] T071 [US1] Create `apps/web/components/inspection/FindingList.tsx` and `FindingCard.tsx` on a plain shadcn `Card` — **no React Bits on a finding card**, since the finding list is a decision-critical surface
- [x] T072 [US1] Create `apps/web/app/inspect/page.tsx` composing the uploader, the viewer, the module toggles, and the findings list, with `VerdictBadge`, `RiskGauge`, and `Disclaimer`
- [x] T073 [P] [US1] Add a Pytest order-independence test in `apps/api/tests/unit/test_detector_purity.py` — detecting fixture A then fixture B in one process yields a result for B byte-identical to a fresh process's result for B
- [x] T074 [P] [US1] Add a Pytest performance test in `apps/api/tests/unit/test_latency.py` — a full single-image inspection reaches a fixed verdict in under 5 s, and a `GET /api/config` round-trip reflects a changed threshold

**Checkpoint**: User Story 1 is fully functional and independently testable. This is the MVP.

---

## Phase 4: User Story 2 — Launchpad Monitor (Priority: P2)

**Goal**: A range safety officer draws a danger zone over a frame and is alerted the moment a
person enters it, from an image, a video, or the live webcam.

**Independent Test**: With a fixture frame containing one person inside a drawn polygon and one
outside, the monitor reports `critical` for the inside person, `ok` for the outside person, and
persists the zone with the run. No language model required.

### Tests for User Story 2

- [x] T075 [P] [US2] Pytest unit test for `cv/zone.py` in `apps/api/tests/unit/test_cv_zone.py` — inside, outside, and edge overlap, with the containment rule (any overlap counts as inside) asserted
- [x] T076 [P] [US2] Pytest unit test for zone validation in `apps/api/tests/unit/test_zone_validation.py` — a polygon with fewer than three points, a self-intersecting outline, and a zero-area polygon are each rejected with a message naming the problem
- [x] T077 [P] [US2] Pytest contract test in `apps/api/tests/contract/test_monitor.py` — `POST /api/monitor/{run_id}/frame` with a raw JPEG body returns findings and `zone_status`; a frame before a zone returns `409`; the response includes `processing_ms`
- [x] T078 [P] [US2] Pytest latency test in `apps/api/tests/unit/test_monitor_latency.py` — a monitored frame is processed server-side in under 500 ms
- [x] T079 [P] [US2] Vitest + RTL for `ZoneEditor` in `apps/web/tests/zone-editor.test.tsx` — drawing, editing, and deleting a polygon, and normalized points round-tripping through the Zustand store
- [x] T080 [P] [US2] Vitest + RTL for the live banner in `apps/web/tests/live-banner.test.tsx` — `CLEAR` / `WARNING` / `DANGER` each render text and an icon, and remain legible with reduced motion and with colour perception differences simulated
- [x] T081 [US2] Playwright e2e in `e2e/monitor-webcam.spec.ts` — using Chromium's `--use-file-for-fake-video-capture`, a person entering the zone shows `DANGER` within 1 second

### Implementation for User Story 2

- [x] T082 [US2] Create `apps/api/cv/zone.py` as a pure function testing normalized bounding regions against a normalized polygon with `cv.pointPolygonTest`
- [x] T083 [US2] Create `apps/api/app/routers/monitor.py` with `POST /api/monitor`, `POST /api/monitor/{run_id}/frame` (raw JPEG in, findings plus `zone_status` out, **no agent on this fast path**), `PUT` and `DELETE /api/monitor/{run_id}/zone`, and `GET /api/monitor/{run_id}/log`
- [x] T084 [US2] Create `apps/web/stores/monitor-store.ts` — the only Zustand store in the app, holding zone points, source selection, and live status
- [x] T085 [US2] Create `apps/web/components/monitor/ZoneEditor.tsx` — a canvas polygon editor storing normalized points, with the malformed-polygon messages from T076 surfaced
- [x] T086 [US2] Create `apps/web/hooks/use-webcam.ts` — `getUserMedia`, offscreen-canvas capture, `toBlob('image/jpeg')`, **single frame in flight** (skip the capture while a request is outstanding), and a disconnected state that marks the last status as stale
- [x] T087 [US2] Create `apps/web/components/monitor/SourceSelector.tsx` using shadcn `Tabs` for image, video file, and webcam
- [x] T088 [US2] Create `apps/web/components/monitor/LiveStatusBanner.tsx` — `CLEAR` / `WARNING` / `DANGER` with text, icon, and colour, an `aria-live` region, and an `AnimatedList` detection log restricted to **status transitions**, not to severity-bearing finding detail
- [x] T089 [US2] Create `apps/web/app/monitor/page.tsx` composing the source selector, the zone editor, the live monitor, the banner, and the detection log, with `Disclaimer`
- [x] T090 [US2] Run `pnpm generate` to regenerate `packages/contract`
- [x] T091 [P] [US2] Add a Pytest test in `apps/api/tests/unit/test_zone_reload.py` — a saved zone re-renders in the same position for a frame of a different size, using the stored `source_width` / `source_height`
- [x] T092 [P] [US2] Add a Pytest test in `apps/api/tests/unit/test_two_tabs.py` — two concurrent SSE subscribers on one run stay consistent and neither corrupts the run

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 — Smoke, Fire, Leak, and Abnormal Motion (Priority: P6)

**Goal**: Smoke, flame, liquid pooling, and unexpected movement near the vehicle base are
flagged, so a developing incident surfaces before an inspection concludes.

> Shipped last, but its fixtures and module can be built in parallel with US2 because the
> dependencies are one-way. The spec explicitly permits US2 to ship with these cues stubbed.

**Independent Test**: Run the cue detectors against fixtures containing a flame region, a smoke
region, a liquid pool, and a static frame with no cues. Each produces a finding of the same shape
as a body or fin finding.

### Tests for User Story 3

- [x] T093 [P] [US3] Pytest fixture test for `cv/cues.py` in `apps/api/tests/unit/test_cv_cues.py` — flame, smoke, liquid, motion, and a clean static frame, each asserting the finding shape matches every other finding type
- [x] T094 [P] [US3] Pytest escalation test in `apps/api/tests/unit/test_cue_escalation.py` — a liquid pool alone is `warning`; a liquid pool with a fire cue in the same run escalates to `critical`

### Implementation for User Story 3

- [x] T095 [P] [US3] Create `apps/api/cv/cues.py` as pure functions — HSV segmentation for flame and smoke, frame differencing for abnormal motion, and a blob detector for liquid pooling — each returning `list[Finding]` on the shared `launchpad_area` step
- [x] T096 [US3] Add the four `cue.*` tool wrappers to `apps/api/agent/tools.py` and register the escalation rule
- [x] T097 [US3] Run `pnpm generate`, then confirm in `apps/web` that cue findings render through the existing `FindingList` with no new component
- [x] T098 [P] [US3] Add a Pytest test in `apps/api/tests/unit/test_cue_degraded.py` — a uniform or too-dark frame yields low confidence from the cue detectors and a `warning` note rather than a clean result

**Checkpoint**: All six user stories are independently functional.

---

## Phase 6: User Story 4 — Agentic Safety Report (Priority: P3)

**Goal**: The engineer watches the agent work through the five checklist steps live, supplies
missing manual inputs when asked, and reads a report whose verdict is provably the rule engine's.

**Independent Test**: Start a run on a fixture image with the mandatory manual inputs deliberately
omitted. The agent reaches step 4, pauses, requests exactly the missing inputs in an in-app form,
accepts them, resumes, and produces a report whose verdict matches the rule engine's independent
output.

### Tests for User Story 4

- [x] T099 [P] [US4] Pytest unit test for the narrative payload in `apps/api/tests/unit/test_narrative_payload.py` — the serialized payload matches a denylist of `data:image`, `base64`, image MIME types, and absolute paths, and contains no run-local image reference (FR-039, SH-009)
- [x] T100 [P] [US4] Pytest unit test for narrative degradation in `apps/api/tests/unit/test_narrative_fallback.py` — with the model forced to fail, the report still carries verdict, risk score, checklist, and reasons, and marks the narrative `unavailable` rather than omitting it (FR-026, SH-008)
- [x] T101 [P] [US4] Pytest verdict-immutability test in `apps/api/tests/unit/test_verdict_immutable.py` — the displayed verdict is byte-identical to the rule engine's independent output even with the narrative forced to fail (SH-006)
- [x] T102 [P] [US4] Pytest interrupt test in `apps/api/tests/unit/test_interrupt.py` — the graph pauses at step 4, `resume` with valid input completes the run, and the same `thread_id` is reused
- [x] T103 [P] [US4] Pytest contract test in `apps/api/tests/contract/test_runs.py` — `POST /api/runs/{run_id}/manual-inputs` rejects a negative wind speed with `400` and `field` set, and the SSE stream delivers the documented event sequence
- [x] T104 [P] [US4] Vitest + RTL for `ManualInputsDialog` in `apps/web/tests/manual-inputs.test.tsx` — a negative wind speed is rejected inline and does not submit
- [x] T105 [US4] Playwright e2e in `e2e/agentic-report.spec.ts` — a run pauses for missing inputs, the dialog submits, the run resumes, and the report renders the verdict with the disclaimer

### Implementation for User Story 4

- [x] T106 [P] [US4] Create `apps/api/agent/state.py` with the `GraphState` `TypedDict`
- [x] T107 [US4] Create `apps/api/agent/graph.py` — the `StateGraph` with the five ordered steps, **`interrupt()` as the first statement of the `weather_manual` node** (the node restarts from the beginning on resume, so anything before the interrupt re-runs), a conditional edge looping back for invalid input, and event emission through `app/events.py`
- [x] T108 [US4] Create `apps/api/agent/narrative.py` building the text-only `NarrativeContext` from a **field allow-list**, calling `gpt-4o-mini` with a 6 s timeout, validating the response into `{narrative, recommended_actions[]}` — a schema with **no verdict field to write into** — and falling back to the template path
- [x] T109 [US4] Create `apps/api/agent/report.py` assembling the report and writing the `reports` row with `narrative_status='pending'` **before** the model call, so a later narrative update touches narrative columns only
- [x] T110 [US4] Create `apps/api/app/routers/runs.py` with `POST /api/runs`, `GET /api/runs/{run_id}/stream` (SSE), `GET /api/runs/{run_id}/events`, `GET /api/runs/{run_id}/required-inputs`, `POST /api/runs/{run_id}/manual-inputs`, `GET /api/runs/{run_id}`, `GET /api/runs/{run_id}/report`, and `GET /api/runs`
- [x] T111 [US4] Run `pnpm generate` to regenerate `packages/contract`
- [x] T112 [US4] Create `apps/web/hooks/use-run-stream.ts` — an `EventSource` reducer maintaining checklist step status, findings, and the awaiting-input state
- [x] T113 [US4] Create `apps/web/components/report/AgentTimeline.tsx` with React Bits motion confined to the step timeline, which UX-003 explicitly permits
- [x] T114 [US4] Create `apps/web/components/report/ManualInputsDialog.tsx` driven by the server's field registry with React Hook Form + Zod built from that registry
- [x] T115 [US4] Create `apps/web/app/report/[runId]/page.tsx` — `VerdictBadge` rendered **statically with no `DecryptedText` reveal**, `RiskGauge`, the pass/fail checklist, ordered reasons, recommended actions, the annotated image, the export control from T127, the "Verdict computed by rules; explanation by AI" attribution, and `Disclaimer` (UX-005)
- [x] T116 [P] [US4] Add a Pytest test in `apps/api/tests/unit/test_report_early_write.py` — a narrative timeout leaves the persisted verdict, risk score, checklist, and reasons byte-identical

**Checkpoint**: The demo's centrepiece works, and the report proves the verdict came from rules.

---

## Phase 7: User Story 5 — Mission Dashboard and History (Priority: P5)

**Goal**: A team lead sees the latest verdict at a glance, browses and filters past runs, and
shares one report read-only.

**Independent Test**: With five stored runs of varying verdicts, the dashboard shows the latest
verdict, risk score, and checklist status, and the history list filters to a single verdict and
opens to the full report.

### Tests for User Story 5

- [x] T117 [P] [US5] Pytest contract test in `apps/api/tests/contract/test_history.py` — `GET /api/runs?verdict=` filters, and `GET /api/runs/latest` returns the dashboard summary
- [x] T118 [P] [US5] Pytest share test in `apps/api/tests/unit/test_share.py` — `POST /api/runs/{run_id}/share` is idempotent, `GET /api/share/{token}` exposes that report and no controls, and a token whose run is gone returns `410 SHARE_NOT_AVAILABLE` rather than a blank report
- [x] T119 [P] [US5] Vitest + RTL for the history table in `apps/web/tests/history.test.tsx` — verdict filtering and pagination
- [x] T120 [US5] Playwright e2e in `e2e/share.spec.ts` — generate a share link, open it in a fresh context, assert the report renders with no run controls and no listing of other runs

### Implementation for User Story 5

- [x] T121 [P] [US5] Add `GET /api/runs` filtering and `GET /api/runs/latest` to `apps/api/app/routers/runs.py`
- [x] T122 [US5] Create `apps/api/app/routers/share.py` with `POST /api/runs/{run_id}/share` and `GET /api/share/{token}`, the latter returning a reduced read-only document with no controls
- [x] T123 [US5] Create `apps/web/components/report/RiskGauge.tsx` using `CountUp` — a permitted React Bits target — with the score banded and colour **never** the sole signal
- [x] T124 [US5] Create `apps/web/app/history/page.tsx` with a shadcn `Table`, a verdict filter, and pagination
- [x] T125 [US5] Create `apps/web/app/page.tsx` — the dashboard: an `Aurora` or `Threads` background via dynamic import, a `ShinyText` / `GradientText` hero, quick-action tiles, the latest verdict, `RiskGauge`, checklist status, and recent runs with skeletons while loading
- [x] T126 [US5] Create `apps/web/app/share/[token]/page.tsx` rendering the read-only report, including the `410` not-available state
- [x] T127 [US5] Extend the print stylesheet in `apps/web/app/globals.css` so the report is legible in black and white, and add a print action on the report page
- [x] T128 [US5] Run `pnpm generate` to regenerate `packages/contract`

**Checkpoint**: All six user stories are independently functional and demonstrable.

---

## Phase 8: User Story 6 — Demo Mode (Priority: P4)

**Goal**: One click, one correct verdict, offline, through the real pipeline — so the hackathon
demo cannot fail on setup or network.

**Independent Test**: With the network disabled, trigger each of the three bundled scenarios in
turn and confirm the expected verdict, annotated image, reasons, and report.

### Tests for User Story 6

- [x] T129 [P] [US6] Pytest offline scenario test in `apps/api/tests/e2e/test_demo_scenarios.py` — all three scenarios yield GO / HOLD / NO-GO with `no_network` enforced, using the template report path
- [x] T130 [P] [US6] Pytest cold-start test in `apps/api/tests/e2e/test_cold_start.py` — with an empty store, all three scenarios still produce their expected verdicts (NFR-007, SC-001)
- [x] T131 [US6] Playwright e2e in `e2e/demo-scenarios.spec.ts` — the three scenarios produce GO, HOLD, and NO-GO in sequence, 10 consecutive passes (SC-001)

### Implementation for User Story 6

- [x] T132 [US6] Seed `demo_scenarios` in `apps/api/db/repo.py` with `normal`, `misaligned_fin`, and `person_near_pad`, each carrying complete `manual_inputs_json` so a demo never pauses
- [x] T133 [US6] Create `apps/api/app/routers/demo.py` with `GET /api/demo/scenarios` and `POST /api/demo/scenarios/{key}/run`, the latter entering the identical pipeline a real run uses (FR-036)
- [x] T134 [US6] Create `apps/web/components/demo/DemoScenarioMenu.tsx` on the dashboard and the inspection page, showing each scenario's expected verdict as metadata
- [x] T135 [US6] Run `pnpm generate` to regenerate `packages/contract`

**Checkpoint**: The three-scenario demo is reliable and offline.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [x] T136 [P] Accessibility pass — keyboard operability, focus rings, `aria-live` on status changes, WCAG AA contrast in the dark theme **and** in black-and-white print, and `prefers-reduced-motion` disabling every decorative animation across the five UX-004 screens; all five usable at 1280px with no horizontal scrolling (Constitution 4.VI, FR-041, FR-042, UX-004, SC-009)
- [x] T137 [P] Hedging and disclaimer audit — assert `Disclaimer` from `apps/web/components/verdict/Disclaimer.tsx` renders on all five UX-004 screens (`apps/web/app/page.tsx`, `apps/web/app/inspect/page.tsx`, `apps/web/app/monitor/page.tsx`, `apps/web/app/report/[runId]/page.tsx`, `apps/web/app/history/page.tsx`), and add a Vitest case in `apps/web/tests/hedged.test.ts` that fails on the banned certainty words and certification claims in `apps/web/lib/hedged.ts` (FR-037, FR-038, UX-004, SH-004, SH-005)
- [x] T138 [P] Secrets audit — assert `OPENAI_API_KEY` appears only in `apps/api/.env.example` and `.env.example`, never in a `NEXT_PUBLIC_*` variable and never in the built `apps/web` bundle (Constitution 5.III)
- [x] T139 [P] React Bits boundary audit — add a Vitest case in `apps/web/tests/react-bits-boundary.test.tsx` asserting no component under `apps/web/components/react-bits/` is rendered inside `apps/web/components/verdict/VerdictBadge.tsx`, `apps/web/components/verdict/SeverityIndicator.tsx`, `apps/web/components/verdict/Disclaimer.tsx`, or `apps/web/components/inspection/FindingList.tsx` (Constitution 4.III)
- [x] T140 Empty, error, and loading states for every screen, an `apps/web/app/error.tsx` boundary, and toasts via `sonner`
- [x] T141 Performance pass in `apps/web/app/page.tsx` and `apps/web/components/monitor/LiveStatusBanner.tsx` — lazy-load heavy React Bits via `next/dynamic`, downscale uploads client-side in `apps/web/lib/upload.ts`, and confirm the dashboard reaches a Lighthouse score of 90 while the live monitor sustains 2 analysed frames per second under 1.5 s end-to-end latency (NFR-001, NFR-002, SC-005, SC-006)
- [x] T142 [P] Fill any coverage gaps in `apps/api/tests/unit/` and `apps/web/tests/`, confirming every CV module still has both a `__pass` and a `__fail` fixture
- [x] T143 Write `README.md` with the architecture diagram, screenshots, the 90-second demo script, and an honest limitations section
- [x] T144 Write `PITCH.md` — "An AI co-pilot for low-cost rocket safety inspection." — with the 3-scenario live demo order GO → HOLD → NO-GO
- [x] T145 Run the full `quickstart.md` validation end to end and record the result in the PR

---

## Requirements Traceability

Every requirement in `spec.md` maps to at least one task. IDs are cited in the task text; this
table is the audit view.

### Functional requirements

| Req | Requirement | Tasks |
|---|---|---|
| FR-001 | Verdict only from findings + manual rules; LLM excluded | T017, T020, T046, T101 |
| FR-002 | Only 3 severities, only 3 verdicts | T014, T041 |
| FR-003 | Risk score 0–100, advisory, confidence-weighted | T018, T042, T123 |
| FR-004 | Thresholds configurable without code change | T015, T027, T074 |
| FR-005 | Error / timeout / low confidence → `warning`, never `ok` | T015, T043, T054, T064, T073 |
| FR-006 | `HOLD` when a mandatory input is absent, each named | T019, T044 |
| FR-007 | JPG/PNG/WebP ≤ 10 MB, drag-drop or picker, instant preview | T066, T069, T056 |
| FR-008 | Reject bad type / oversize / corrupt, start no run | T055, T066, T069 |
| FR-009 | Findings for cracks, dents, damage, burn, fin angle, missing parts | T061, T062, T052 |
| FR-010 | Overlay per finding, toggled per module | T063, T070, T057 |
| FR-011 | Fin > 3° `warning`, > 6° `critical` | T015, T062, T053 |
| FR-012 | Draw / edit / delete zone, normalized 0–1 + source dims | T076, T079, T082, T083, T085 |
| FR-013 | Saved zone re-renders at any display size | T085, T091 |
| FR-014 | Person in zone → `critical`; non-person configurable; outside → none | T015, T082, T083 |
| FR-015 | ≥ 2 fps, < 1.5 s, image or video alternative source | T078, T087, T141 |
| FR-016 | Banner `CLEAR`/`WARNING`/`DANGER` by text + icon + colour; audible toggle | T080, T088 |
| FR-017 | Chronological detection log | T083, T088 |
| FR-018 | Flame, smoke, abnormal motion vs consecutive frames | T093, T095 |
| FR-019 | Liquid pooling `warning`, escalates to `critical` with fire | T094, T095, T096 |
| FR-020 | Cue findings identical in shape and rendering | T093, T095, T097 |
| FR-021 | Fixed checklist order, each step streamed live | T107, T112, T113 |
| FR-022 | Pause at manual inputs, request exactly the missing, auto-resume | T102, T107, T114 |
| FR-023 | Range validation, inline rejection, no submit | T104, T110, T114 |
| FR-024 | Report: verdict, risk, per-step pass/fail, ordered reasons, actions, images, timestamp, run id | T109, T115 |
| FR-025 | "Verdict computed by rules; explanation by AI", verdict unchanged | T101, T115 |
| FR-026 | Template report on LLM failure, narrative marked unavailable | T100, T108 |
| FR-027 | Hedged language, no certification claim, no verdict change | T033, T108, T137 |
| FR-028 | Collect wind / visibility / precipitation / area-cleared / notes, persisted | T019, T022, T110 |
| FR-029 | Wind > 10 `warning`, > 15 `critical`; poor vis; heavy precip; area not cleared `critical` | T019, T044 |
| FR-030 | Those four mandatory; absence → `HOLD` | T019, T041, T044 |
| FR-031 | Dashboard: latest verdict, risk gauge, checklist status, recent runs | T123, T125 |
| FR-032 | List runs, filter by verdict, open full report | T119, T121, T124 |
| FR-033 | Print/PDF legible in B&W, read-only share link, no controls | T120, T122, T126, T127 |
| FR-034 | "Load demo scenario" menu, exactly three, one click | T132, T133, T134 |
| FR-035 | Demo works offline via the template report path | T129, T133 |
| FR-036 | Demo runs the real pipeline, not pre-rendered results | T129, T133 |
| FR-037 | Disclaimer on every screen showing a verdict, risk, or findings | T037, T137 |
| FR-038 | No certification claim, no unwarranted certainty | T033, T137 |
| FR-039 | No image data to any third party; text summary only | T099, T108 |
| FR-040 | Local storage only; no account or sign-in | T006, T021, T138 |
| FR-041 | Text + icon besides colour; AA contrast in dark and B&W | T036, T038, T050, T136 |
| FR-042 | Keyboard-operable; decorative motion disabled on reduced motion | T039, T051, T136 |
| FR-043 | Measurement carries error margin near a decision threshold | T014, T045, T062 |

### Non-functional, UX, and success criteria

| Req | Requirement | Tasks |
|---|---|---|
| NFR-001 | Inspection under 5 s on a 1280px laptop | T074, T141 |
| NFR-002 | Monitored frame under 500 ms server-side | T078 |
| NFR-003 | No module failure may crash, hang, or abort a run | T054, T064, T098 |
| NFR-004 | Usable at 1280px, usable on tablet | T136, T141 |
| NFR-005 | Images in memory/local only for the run's lifetime | T021, T022, T143 |
| NFR-006 | Single laptop, no external dependency, demo works with no LLM | T129, T143 |
| NFR-007 | Three scenarios reproducible cold with no prior runs | T130 |
| UX-001 | Dark mission-control default theme | T040, T125 |
| UX-002 | Large decision badge, distinct icon + text per verdict | T036, T050 |
| UX-003 | Motion only for atmosphere; never on badge, findings, severity, disclaimer | T113, T123, T139 |
| UX-004 | Exactly the five named screens | T072, T089, T115, T124, T125 |
| UX-005 | Report screen: timeline, dialog, verdict, checklist, actions, export | T113, T114, T115, T127 |
| UX-006 | Monitor screen: source selector, zone editor, banner, log | T083, T085, T087, T088, T089 |
| UX-007 | Inspection screen: uploader, overlay toggles, annotated results | T069, T070, T072 |
| SC-001 | Three scenarios correct in 10 of 10 consecutive runs | T131 |
| SC-002 | Fin angles within 1.5° of known on the reference set | T045, T052, T053 |
| SC-003 | Person entering the zone shows `DANGER` fast | T081 |
| SC-004 | A first-time user can state the verdict and name a reason | T071, T143 |
| SC-005 | Inspection reaches a verdict in under 5 s | T074, T141 |
| SC-006 | ≥ 2 fps sustained, < 1.5 s end-to-end | T078, T141 |
| SC-007 | An engineer inspects and reads the verdict unaided | T058, T105 |
| SC-008 | Offline demo still completes and still yields its verdict | T129, T130 |
| SC-009 | Five screens usable at 1280px, no horizontal scroll | T136 |
| SH-001 | One module forced to fail → run still completes, verdict degraded not absent | T054, T064 |
| SH-002 | Every module forced to fail → no crash, hang, or absent verdict | T054, T064, T098 |
| SH-003 | 100% of findings show module, check id, severity, confidence, message | T014, T050 |
| SH-004 | No certification / approval / guaranteed-safety strings | T033, T137 |
| SH-005 | Every verdict, finding, and narrative string passes hedging review | T033, T108, T137 |
| SH-006 | Displayed verdict byte-identical to rule engine output, 10 of 10 | T101, T116 |
| SH-007 | A measurement inside its error margin shows the non-distinguishable note | T045, T062, T115 |
| SH-008 | Model disabled → template report still complete, marked unavailable | T100, T108 |
| SH-009 | No image data reaches a third party in 10 of 10 trials | T099, T138 |
| SH-010 | Every detection module has a pass and a fail fixture test | T052, T053, T093, T142 |

**Coverage**: 43/43 FR · 7/7 NFR · 7/7 UX · 9/9 SC · 10/10 SH = **76/76**.

The 48 tasks not cited above are infrastructure rather than requirements: toolchain, workspace,
and CI setup (T001–T005, T007, T009–T013), the shadcn and provider wiring (T008, T035),
persistence and
streaming plumbing (T023–T026, T028–T032), the SSE proxy route (T034), the check-id registry and
CV plumbing that feed cited requirements (T016, T059, T060, T065, T067, T075, T084, T086), the
graph state module (T106), repeated `pnpm generate` regenerations (T029, T068, T090, T111, T128,
T135), supporting tests already covered by the requirement they exercise (T047, T048, T049, T077,
T092, T103, T117, T118), and documentation, empty-state, and end-to-end validation work (T140,
T144, T145). Every requirement is
traceable; not every task traces to a numbered requirement.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies — start immediately
- **Foundational (Phase 2)**: depends on Setup; **blocks all user stories**
- **User Stories (Phases 3–8)**: all depend on Foundational; independent of each other except
  where noted
- **Polish (Phase 9)**: depends on the stories you intend to ship

### User story dependencies

- **US1 (P1)**: no story dependencies. **Start here.** It is the MVP.
- **US2 (P2)**: no story dependencies. Builds on the `Finding` type and the upload path from US1,
  but is independently testable against its own fixtures.
- **US4 (P3)**: depends on US1's tools (`agent/tools.py`) and on Foundational. The report renders
  findings that US1 and US2 produce, but the graph is testable against synthetic `Finding` lists.
- **US6 (P4)**: depends on the full pipeline (US1 + US4) to be demonstrable end to end, but its
  scenario seeding and router are testable earlier.
- **US5 (P5)**: depends on completed runs existing. Purely a presentation layer.
- **US3 (P6)**: no blocking dependencies. Its fixtures and module can be built in parallel with
  US2; it attaches to the `launchpad_area` step, so it lands after US2 wires that step.

### Within each user story

- Tests are written first and **must fail** before implementation
- Models before services, services before endpoints
- Regenerate `packages/contract` after any API change, **before** the web task that consumes it
- Story complete before moving to the next priority

### Parallel opportunities

- All `[P]` tasks within a phase can run concurrently — they touch different files
- T008–T013 in Setup are all independent
- T014–T016, T021, T027, T031–T033, T035–T38 in Foundational are all independent
- T059–T063, T069–T071 in US1 are all independent of each other
- Once Foundational is complete, US1, US2, US3, and US5 can be worked in parallel by different
  people; US4 needs US1's tools

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (write first, watch them fail):
T052  Pytest fixture test for cv/body.py
T053  Pytest fixture test for cv/fins.py
T054  Pytest fail-safe test
T055  Pytest contract test for POST /api/inspections
T056  Vitest + RTL for the uploader
T057  Vitest + RTL for AnnotatedViewer

# Then the independent CV modules together:
T059  cv/frameio.py
T060  cv/models.py (YOLOv8n singleton)
T061  cv/body.py
T062  cv/fins.py
T063  cv/annotate.py
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1 Setup (T001–T013)
2. Phase 2 Foundational (T014–T051) — **blocks everything**
3. Phase 3 User Story 1 (T052–T074)
4. **Stop and validate**: run US1's independent test with the network disabled
5. Demo if ready

### Incremental delivery

1. Setup + Foundational → a verdict is computable with no model
2. US1 → demoable inspection (MVP)
3. US2 → demoable live monitoring
4. US4 → demoable agentic report with the interrupt flow
5. US6 → reliable one-click demo, offline
6. US5 → dashboard, history, sharing
7. US3 → hazard cues

### The demo path

The demo-critical path is **US1 + US4 + US6**. A run of the three scenarios exercises the inspection
pipeline, the agent graph with a pre-filled manual-input set, the rule engine, and the template
report path. US2 and US5 make the product credible to a judge; US3 makes it safety-relevant.
Under time pressure, cut **US3 first**, then video-file mode and the Chromium fake-webcam e2e —
those are the two most expensive items for the least demo value.

### Parallel Team Strategy

With multiple developers:

1. The team completes **Phase 1 Setup + Phase 2 Foundational** together. The rule engine, the
   event substrate, and the web foundations are the shared floor and cannot be split
2. Once Foundational is done, work fans out by story:
   - Developer A: User Story 1 (Pre-Launch Inspection) — the MVP
   - Developer B: User Story 2 (Launchpad Monitor)
   - Developer C: User Story 3 (Smoke / Fire / Leak) — small, and safe to pick up late
3. User Stories 4, 5, and 6 need US1 in place, so they follow it rather than running beside it
4. Stories integrate independently; `packages/contract` is regenerated at each integration point,
   never hand-merged

---

## Hackathon 8-Hour Order

The supplied hour-by-hour **shape** — setup, foundations, the two demo-heavy stories, the agent
report, the one-click demo, presentation, hardening, polish — mapped onto this file's task IDs.
Note it is an *agenda*, not a dependency order: H2 is the gate, and nothing in H3+ is demoable
until it lands.

| Hour | Tasks | Phase | Note |
|---|---|---|---|
| H1 | T001–T013 | Setup | T011 fixtures gate every CV test — do not defer it |
| H2 | T014–T051 | Foundational | The rule engine, event substrate, and web foundations. **The gate: nothing else is demoable until this is green** |
| H3–4 | T052–T074 (US1), then T075–T092 (US2) | US1, US2 | The bulk of the demo value. US1 first — it is the MVP |
| H5 | T099–T116 (US4), T129–T135 (US6) | US4, US6 | The interrupt flow and the one-click offline demo |
| H6 | T117–T128 (US5) | US5 | Presentation layer; needs stored runs from H3–5 |
| H7 | T129–T131, T136–T139 | US6 tests, audits | Harden the demo path and the four safety audits |
| H8 | T140–T145, **cut T093–T098 (US3) if behind** | Polish | Polish and pitch |

**Cut list, in order**, if the clock runs out: US3 cues (T093–T098) → video-file mode → the
Chromium fake-webcam e2e → Lighthouse 90 → `PITCH.md`. Never cut: the rule engine (T014–T020),
the fail-safe decorator (T064) and its test (T054), the rule-engine isolation guard (T020/T046),
or the disclaimer and React Bits audits (T137/T139).

---

## Notes
- `[USn]` maps to `spec.md` user stories for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- One task equals one commit, Conventional Commits
- Stop at any checkpoint to validate the story independently
- A task is done only when every condition in Constitution §7 holds: compiles with no type errors,
  lint passes, its tests pass, it is visible in the UI if user-facing, and it matches the `spec.md`
  acceptance criteria
- If a task would violate a MUST, **stop and resolve it** — record the deviation in `plan.md`
  Complexity Tracking, or amend the constitution explicitly via `/sp.constitution`. Do not weaken
  the task
