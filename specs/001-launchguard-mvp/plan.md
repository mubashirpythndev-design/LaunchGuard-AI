# Implementation Plan: LaunchGuard AI MVP

**Branch**: `001-launchguard-mvp` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-launchguard-mvp/spec.md`
**Constitution**: `.specify/memory/constitution.md` v1.0.0 (ratified 2026-09-29)
**Phase 0 output**: [research.md](./research.md)

## Summary

Three modes — Pre-Launch Inspection, Launchpad Monitor, and AI Safety Report — built as two
deployables bound by one generated contract. `apps/api` (Python 3.11, FastAPI) runs stateless
OpenCV + YOLOv8n detection behind pure `(input) -> Finding` tools, an agent that orchestrates
those tools with LangGraph, and an isolated deterministic rule engine that is the sole producer
of the GO / HOLD / NO-GO verdict. `apps/web` (Next.js App Router, TypeScript strict) is a dark
mission-control client that streams every checklist step live over SSE and consumes a contract
generated from the API's OpenAPI document. The language model is invoked only after the verdict
is persisted, receives a text-only summary, and may explain and recommend but cannot alter the
decision; when it is absent, a template report is still produced.

Phase 0 resolved ten decisions that changed the input plan, three of them materially: the pause
is LangGraph's native `interrupt()` with a persistent checkpointer rather than an `asyncio.Event`
(R2), the risk score is verdict-banded and saturating rather than a saturating sum (R7), and the
`DecryptedText` verdict-badge animation is removed as a Constitution 4.III violation (R3).

## Technical Context

**Language/Version**: TypeScript 5 (`strict: true`, no `any`) + Python 3.11
**Primary Dependencies**: Next.js 15 (App Router, Turbopack), React 19, Tailwind CSS v4, shadcn/ui,
React Bits (shadcn registry, `TS-TW` variants), TanStack Query, React Hook Form, Zod v4, FastAPI,
Pydantic v2, Ultralytics YOLOv8n, OpenCV (`opencv-python`), LangGraph with
`langgraph-checkpoint-sqlite`, OpenAI `gpt-4o-mini`, `@hey-api/openapi-ts`
**Storage**: SQLite via SQLAlchemy 2 (runs, findings, events, reports, danger zones) plus
`AsyncSqliteSaver` for LangGraph checkpoints — both swappable without touching CV or agent code
**Testing**: Pytest with fixture images, mypy `--strict`, Ruff · Vitest + React Testing Library,
Playwright (one spec per demo scenario), ESLint + Prettier
**Target Platform**: Single laptop — Linux, macOS, or Windows; 1280px-wide browser is the primary
target, tablet secondary. No container, no external service. Node 22+, Python 3.11+
**Project Type**: web — exactly two deployables (`apps/web`, `apps/api`) and one generated
contract package (`packages/contract`); see Structure Decision
**Performance Goals**: Single-image inspection reaches a fixed verdict in < 5 s (NFR-001, SC-005);
one monitored frame is processed server-side in < 500 ms (NFR-002); live monitor sustains ≥ 2
analysed frames/s with end-to-end latency < 1.5 s (FR-015, SC-006); zone `DANGER` status appears
within 1 s of entry (SC-003); fin angle within 1.5° of known value (SC-002); narrative never
blocks the verdict (6 s hard timeout, R11)
**Constraints**: No image bytes, absolute pixel coordinates, or recoverable encoding of image
content may reach any third party (FR-039, SH-009); `OPENAI_API_KEY` is server-side only
(Constitution 5.III); the API runs as a **single uvicorn worker** (R5); the product is fully
demonstrable with the network disabled and the model unavailable (NFR-006, SC-008); a
module failure may never crash, hang, or abort a run (NFR-003)
**Scale/Scope**: 1 operator, 1 machine, 2 deployables, 3 modes, 5 screens, 3 demo scenarios,
15 stable check ids across 5 ordered checklist steps, 43 FRs / 7 NFRs / 7 UX requirements /
9 success criteria. Thermal, drone, vibration, telemetry, and digital-twin work are explicitly
deferred (Constitution 6.II)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md`. Every MUST below is blocking; a violation must be
resolved by changing the plan, or justified in Complexity Tracking — never by reinterpreting the
principle.*

**Pre-research evaluation** (performed before Phase 0): all eleven gates passed on the
specification as written. Two findings were carried into research rather than accepted:
the low-confidence threshold was unset (Constitution 2.II `TODO(CONFIDENCE_FLOOR)`), and the
`Finding` entity had no representation for measurement error margin (FR-043/SH-007).

**Post-design re-evaluation** (performed after Phase 1, below).

- [x] **S1 Deterministic verdict** — `rule_engine/` computes the verdict from findings and
  manual-input rule results using the fixed order in spec "Verdicts, Severity, and Risk Score",
  and imports nothing from `cv/` or `agent/`, so no model can reach it (R6). The LLM is invoked
  only after the verdict row is committed, and its output schema
  (`{narrative, recommended_actions[]}`) contains no field a verdict could be written into, so
  escalation-only behaviour is structural rather than prompt-enforced (R11). `test_verdict.py`
  asserts the engine's output is unchanged with the model forced to fail. (Constitution 2.I)
- [x] **S2 Fail safe** — `apply_confidence_floor()` in `rule_engine/config.py` makes any check
  below `MIN_CONFIDENCE_FOR_OK = 0.35` unable to be recorded as `ok`; errored, timed-out, and
  skipped modules emit `warning` at `confidence=0.0` with `degraded=true`; a missing mandatory
  manual input yields `HOLD` with each absent input named (FR-006, FR-030); all-checks-failed
  yields `HOLD`, never `GO`; and a run interrupted by an API restart is marked `failed` with a
  reason rather than resumed toward a verdict (R12). The one-way-floor reading of 2.II against
  the spec's low-confidence person-in-zone edge case is resolved in R8 and recorded so
  `/sp.analyze` can classify it as resolved-by-construction, not reinterpreted. (Constitution 2.II)
- [x] **S3 Explainable** — `rule_engine/types.py` defines one `Finding` dataclass carrying module,
  check id, severity, message, confidence, and `Measurement[]`, with an optional `Overlay`. It is
  the *same* type the engine consumes and `cv` returns, so a finding missing any field does not
  type-check and cannot enter a decision (R6). The `Measurement` record is what makes FR-043
  satisfiable at all (R9). Overlays are emitted by the seven visual modules and are absent only
  for `zone.occupancy` and the four manual rules, which describe a region or a scalar rather
  than an object box — the one documented exception, matching the specification's own
  Constitution Alignment block. (Constitution 2.III)
- [x] **S4 Honest uncertainty** — the disclaimer *"Decision-support tool. Not a replacement for
  certified range safety."* is served by `GET /api/config`, stored on every `reports` row, and
  rendered from a single `<VerdictBadge>` component mounted on all five screens, so the live
  screen, the shared link, and the print view emit the identical string (FR-037, SH-004); a
  shared `hedged()` helper constructs all
  finding and narrative copy, and `test_hedging.py` fails the build on banned certainty words
  and on certification claims (FR-038, SH-005); a `critical` finding below the confidence floor
  additionally carries `low_confidence_critical=true` and an explicit "produced by the fail-safe
  rule" note (R8); the ambiguity note required by SH-007 is generated from
  `is_threshold_ambiguous()` (R9). `DecryptedText` was removed from the verdict badge (R3).
  (Constitution 2.IV)
- [x] **S5 Vision proposes** — the agent calls CV modules only through typed tools with the
  `(input) -> Finding` signature; it computes no measurement, and every metric in a report
  originates in a `Measurement` produced by a detection step. The narrative payload is built by
  field allow-list from those results (R11), and FR-036's demo path runs the identical pipeline,
  so no number can exist without a tool behind it. (Constitution 2.V)
- [x] **A1 Two deployables, one contract** — `apps/web` and `apps/api` are the only
  deployables. `packages/contract/openapi.json` is dumped from `app.openapi()` with no server
  running, and `@hey-api/openapi-ts` with the Zod v4 plugin generates both the TypeScript types
  and the Zod schemas from that one file (R1). `packages/contract/src/` is generated and
  git-ignored; `apps/web/lib/schemas.ts` contains only re-exports from `@launchguard/contract`
  and no type declarations. CI regenerates and runs `git diff --exit-code`, so a stale contract
  is a build failure. (Constitution 3.I)
- [x] **A2 CV in Python only** — all detection is in `apps/api/cv/`. The browser obtains frames
  via `getUserMedia`, draws them to an offscreen canvas, `toBlob('image/jpeg')`, and POSTs bytes;
  it performs no CV, loads no model, and contains no OpenCV.js (R4). The only browser-side image
  work is drawing the user's own returned overlay for display. (Constitution 3.II)
- [x] **A3 Pure tools, streaming, persistence** — every agent tool is `(input) -> Finding` with
  typed input and output, holds no cross-request state, and is fixture-tested; the YOLOv8n
  instance is a lazily created singleton holding *weights* only, with an order-independence test
  proving it (R10). Progress streams over SSE through a persisted event log with monotonic
  per-run sequence numbers, `Last-Event-ID` replay, and a 15 s heartbeat (R5); events map onto
  `stream_events(version="v3")`'s `interrupts` / `interrupted` / `output` (R2). Runs, findings,
  events, reports and zones live in SQLite via SQLAlchemy 2 (Constitution 3.V), and the API runs
  a single worker, which the in-process pub/sub requires (R5). (Constitution 3.III–3.V)
- [x] **F1 Frontend discipline** — `strict: true` with no `any` and `@ts-ignore` permitted only
  with a stated reason; every button, dialog, tab, table, and toast comes from `components/ui`
  via the shadcn CLI; the only React Bits mounted are `Threads`/`Aurora` (background), `Counter`
  (risk gauge), and `SpotlightCard` (card surface), each behind a `useReducedMotion()` guard
  that skips mounting entirely, and none appears on the verdict badge, finding list, severity
  indicators, or disclaimer (R3, UX-003); dark mission-control Tailwind theme on shadcn CSS
  variables; server data via TanStack Query, forms via React Hook Form + Zod, Zustand confined to
  the live-monitor store; decision state carried by text + icon + colour together and
  black-and-white-legible via a print stylesheet (FR-041); Server Components by default with
  `"use client"` only on the uploader, zone editor, live monitor, timeline, and report actions.
  (Constitution 4.I–4.VII)
- [x] **Q1 Quality bar** — ESLint 9 flat config + Prettier in `apps/web`, Ruff + `mypy --strict`
  in `apps/api`; Vitest + React Testing Library for components and hooks, Playwright with one
  spec per demo scenario asserting the expected verdict, Pytest with real fixture images where
  every CV module has both a `__pass` and a `__fail` fixture (R14); the demo-scenario fixtures
  *are* the canonical pass/fail members, so the assets shown to judges are the assets CI
  verified; `.env.example` lists `OPENAI_API_KEY`, `DATABASE_URL`, `OPENAI_MODEL`,
  `LOG_LEVEL` and `CORS_ORIGINS`, and a CI grep asserts the key is absent from `apps/web` and
  from any `NEXT_PUBLIC_*` variable. (Constitution 5.I–5.IV)
- [x] **S6 Scope** — the plan implements exactly the three modes of Constitution 6.I, with
  Dashboard, History, and Demo Mode as supporting surfaces, and exactly the three demo
  scenarios. Thermal, drone, telemetry, and digital twin appear in no module, route, UI, or
  string; vibration analysis and ground-control integration are also absent, per the
  specification's Out of Scope list. Where the input plan proposed OpenCV colour-threshold smoke
  and fire detection, that is retained as an MVP cue check (`cue.smoke`, `cue.fire`) because
  Story 3 requires it — it is a cue detector, not the deferred thermal work, and the two are
  never conflated in code or copy. (Constitution 6.I–6.III)

*Result: eleven of eleven gates pass. No gate required a Complexity Tracking entry.*

## Deterministic Decision Model

Recorded here because the specification assigns both the risk formula and the confidence
threshold to planning. Full rationale in [research.md](./research.md) R6–R9.

**Verdict** — computed in `rule_engine/verdict.py`, in this order and no other:

1. any finding `critical`, or any manual rule at `critical` → **NO-GO**
2. otherwise any finding `warning`, any manual rule at `warning`, or any missing mandatory
   manual input → **HOLD**
3. otherwise → **GO**

**Confidence floor** — `MIN_CONFIDENCE_FOR_OK = 0.35`, in `rule_engine/config.py` and exposed via
`GET /api/config`. Applied as a one-way floor: it promotes `ok` to `warning` and never reduces
`warning` or `critical`. Errored, timed-out, and skipped checks emit `warning` at `confidence=0.0`
with `degraded=true`.

**Risk score** — integer 0–100, advisory, never an input to the verdict:

```text
warning_evidence  = Σ over warning findings  of (0.25 × confidence)   # capacity 2.0
critical_evidence = Σ over critical findings of (1.00 × confidence)   # capacity 3.0
low_confidence   = Σ over ok findings where 0 < confidence < 0.35 of (0.35 − confidence)

GO     → round(100 × min(0.30, low_confidence / 0.60))                  # band  0–30
HOLD   → round(40 + 29 × min(1.0, warning_evidence / 2.0))              # band 40–69
NO-GO  → round(70 + 30 × min(1.0, critical_evidence / 3.0))             # band 70–100
```

**Measurement ambiguity** — `Measurement{name, value, unit, error_margin, threshold}`;
`is_threshold_ambiguous()` marks a measurement within its own error margin of a threshold, and
the report then states the outcome is not distinguishable from the adjacent severity
(FR-043, SH-007). Fin alignment declares `error_margin = 1.5°`, matching SC-002.

## Project Structure

### Documentation (this feature)

```text
specs/001-launchguard-mvp/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
apps/
├── web/                          # Next.js 15 (App Router) + TypeScript strict
│   ├── app/
│   │   ├── page.tsx              # Landing / Dashboard
│   │   ├── inspect/page.tsx      # Pre-Launch Inspection
│   │   ├── monitor/page.tsx      # Launchpad Monitor
│   │   ├── report/[runId]/page.tsx
│   │   ├── history/page.tsx
│   │   ├── share/[token]/page.tsx
│   │   └── api/[...path]/route.ts   # SSE-safe proxy to apps/api (R5)
│   ├── components/
│   │   ├── ui/                   # shadcn/ui primitives (CLI-managed)
│   │   ├── react-bits/           # React Bits @react-bits registry — atmosphere only
│   │   ├── verdict/              # VerdictBadge, SeverityIndicator, Disclaimer, RiskGauge
│   │   ├── inspection/           # Uploader, OverlayViewer, ModuleToggles, FindingList
│   │   ├── monitor/              # SourceSelector, ZoneEditor, LiveBanner, DetectionLog
│   │   └── report/               # AgentTimeline, ManualInputForm, Checklist, Actions, Share
│   ├── lib/
│   │   ├── schemas.ts            # re-exports ONLY from @launchguard/contract (R1)
│   │   ├── api-client.ts         # generated SDK
│   │   ├── sse.ts                # EventSource + Last-Event-ID reconnect
│   │   └── hedged.ts             # single source of hedged user-facing copy
│   ├── stores/monitor-store.ts   # Zustand — live-monitor store only
│   └── tests/                    # Vitest + React Testing Library
├── api/                          # Python 3.11 + FastAPI
│   ├── app/
│   │   ├── main.py               # app factory, lifespan, startup recovery (R12)
│   │   ├── config.py             # pydantic-settings; OPENAI_API_KEY read here only
│   │   ├── events.py             # SSE pub/sub + persisted run_events (R5)
│   │   ├── openapi.py            # app.openapi() document assembly
│   │   └── routers/              # inspect, monitor, runs, share, report, config, health
│   ├── agent/
│   │   ├── graph.py              # StateGraph, fixed 5-step order, interrupt (R2)
│   │   ├── tools.py              # pure (input) -> Finding tool wrappers
│   │   ├── narrative.py          # text-only NarrativeContext + template fallback (R11)
│   │   └── state.py              # GraphState TypedDict
│   ├── cv/
│   │   ├── models.py             # YOLOv8n lazy singleton — weights only (R10)
│   │   ├── body.py               # cracks, dents, damage, burn marks, missing parts
│   │   ├── fins.py               # fin alignment, error_margin 1.5°
│   │   ├── zone.py               # normalized-polygon containment
│   │   ├── cues.py               # smoke, fire, leak, motion
│   │   └── frameio.py            # decode/validate; uniform/dark/bright -> low confidence
│   ├── rule_engine/
│   │   ├── types.py              # Severity, Verdict, Measurement, Finding, Thresholds
│   │   ├── config.py             # MIN_CONFIDENCE_FOR_OK, thresholds, risk capacities
│   │   ├── verdict.py            # the three-rule order
│   │   ├── risk.py               # banded saturating score
│   │   ├── manual.py             # wind/visibility/precipitation/area_cleared rules
│   │   └── registry.py           # 15 check ids mapped to 5 ordered steps (R6)
│   ├── db/
│   │   ├── base.py               # engine, session factory
│   │   ├── models.py             # Run, Finding, DangerZone, ChecklistStep,
│   │   │                         #   ManualInput, RunEvent, Report, DemoScenario
│   │   └── repo.py               # data access only
│   └── tests/
│       ├── fixtures/images/      # {check_id}__pass / __fail (R14)
│       ├── unit/                 # Pytest: rule engine, tools, narrative, risk bands
│       ├── contract/             # OpenAPI conformance + generation drift
│       └── e2e/                  # the 3 demo scenarios, headless, network-disabled
packages/
└── contract/                     # Constitution 3.I — generated TS types + Zod schemas
    ├── openapi.json              # dumped from apps/api, no server needed
    ├── openapi-ts.config.ts      # @hey-api/openapi-ts + zod plugin, compatibilityVersion 4
    ├── package.json              # "generate" script; "prebuild" hook
    └── src/                      # GENERATED — git-ignored, never hand-edited
scripts/                          # export_openapi.py, dev orchestration, fixture seeding
e2e/                              # Playwright — one spec per demo scenario (GO, HOLD, NO-GO)
scripts/                          # export_openapi.py, dev up/down, fixture seeding
```

**Structure Decision**

| Area | Lands in | Rationale |
|---|---|---|
| Detection (cracks, dents, damage, burn marks, fins, zone, cues) | `apps/api/cv/` | Constitution 3.II — CV in Python only; the browser does capture, upload, render. |
| Verdict, severity, risk, manual rules, threshold config | `apps/api/rule_engine/` | Constitution 2.I. Owns the decision types; imports nothing from `cv/` or `agent/` (R6). |
| Orchestration, pause/resume, narrative | `apps/api/agent/` | Constitution 2.V / 3.IV. Consumes tools, never re-implements them. |
| Persistence and event log | `apps/api/db/` | Constitution 3.V — SQLAlchemy only, so SQLite can be swapped without touching CV or agent code. |
| API surface, SSE, upload validation, share tokens | `apps/api/app/routers/` | Transport only. No decision or detection logic. |
| All five screens, verdict UI, streaming client | `apps/web/` | Constitution 4 — with the decision-critical components isolated from React Bits. |
| Wire types, validators, SDK | `packages/contract/` | Constitution 3.I — generated from `apps/api`, never authored. |

The contract is **generated from `apps/api`**, not authored: `scripts/export_openapi.py` imports
the FastAPI app and calls `app.openapi()`, then `@hey-api/openapi-ts` produces the TypeScript
types and Zod v4 schemas (R1). `apps/web` declares no API type of its own; `lib/schemas.ts` is
re-exports only. The three mandated top-level directories are `apps/web/`, `apps/api/`, and
`packages/contract/`, exactly as Constitution 3.I names them. `e2e/` and `scripts/` are the two
supporting directories the plan template already lists; neither is a deployable and neither
introduces a fourth one.

**Two directories in the template tree were renamed, not added.** The template lists
`apps/api/agent/`, `apps/api/cv/`, `apps/api/rule_engine/`, and `apps/api/db/` as siblings under
`apps/api/`. That is the layout used, with the FastAPI application itself in `apps/api/app/`.
The input plan's `apps/api/app/cv/` and `apps/api/app/agent/` nesting was rejected because it
puts detection logic inside the transport package, which weakens the boundary Constitution 3.II
is written to protect.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No entries. All eleven Constitution Check gates pass after design, so no MUST is relaxed,
reinterpreted, or justified away. Two design choices are recorded here for review visibility even
though they violate no MUST:

| Choice | Why it is not a violation |
|---|---|
| No Turborepo (R13) | The template and Constitution mandate the two-deployable layout; they mandate no task runner. `pnpm -r` plus `prebuild` hooks cover a three-package workspace. |
| In-process SSE pub/sub, single uvicorn worker (R5) | NFR-006 and spec Assumption 11 define a single-operator, single-machine deployment. The limitation is documented in `quickstart.md` rather than hidden, and the persistence layer it builds on is the same one a broker would replace. |
