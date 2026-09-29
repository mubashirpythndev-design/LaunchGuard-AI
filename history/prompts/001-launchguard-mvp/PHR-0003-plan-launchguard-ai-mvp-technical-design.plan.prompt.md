---
id: PHR-0003
title: Plan LaunchGuard AI MVP Technical Design
stage: plan
date: 2026-09-29
surface: agent
model: opencode/big-pickle
feature: 001-launchguard-mvp
branch: 001-launchguard-mvp
user: mubashirpythndev-design
command: /sp.plan
labels: [plan, research, architecture, contract-generation, streaming, rule-engine, constitution-check, langgraph, sse]
links:
  spec: specs/001-launchguard-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-launchguard-mvp/plan.md
  - specs/001-launchguard-mvp/research.md
  - specs/001-launchguard-mvp/data-model.md
  - specs/001-launchguard-mvp/contracts/api.md
  - specs/001-launchguard-mvp/contracts/events.md
  - specs/001-launchguard-mvp/quickstart.md
  - AGENTS.md
  - history/prompts/001-launchguard-mvp/PHR-0003-plan-launchguard-ai-mvp-technical-design.plan.prompt.md
tests:
  - no executable code produced; plan-phase validation only
  - external-fact verification of 3 researched decisions (contract generator, LangGraph interrupt, React Bits registry)
  - Constitution Check re-evaluated post-design: 11 of 11 gates pass, 0 Complexity Tracking entries
---

## Prompt

> **Provenance note**: the original `/sp.plan` argument was a long technical plan supplied by the
> user. The substance is reproduced below in full; it is a faithful reconstruction rather than a
> byte-for-byte transcript, because the verbatim text was not carried forward into this stage's
> context. Nothing in it was added by the assistant.

Build the technical plan for LaunchGuard AI MVP on branch `001-launchguard-mvp`, per
`specs/001-launchguard-mvp/spec.md` and the constitution at `.specify/memory/constitution.md`.

**Stack** — Next.js 15 App Router, React 19, TypeScript strict, Tailwind CSS v4, shadcn/ui,
React Bits for atmosphere, FastAPI + Pydantic v2, Ultralytics YOLOv8n (`yolov8n.pt`), OpenCV,
LangGraph with an `interrupt` (asyncio `Event`) for missing manual inputs, OpenAI `gpt-4o-mini` for
the narrative, SQLite + SQLAlchemy, SSE for streaming run progress, POST for webcam frames.

**Structure** — monorepo with a `launchguard/` wrapper:

```text
launchguard/
├── apps/
│   ├── web/            # Next.js 15 App Router, TypeScript strict, shadcn/ui, React Bits
│   └── api/
│       ├── app/
│       │   ├── main.py
│       │   ├── cv/         # YOLO detectors, OpenCV pre-processing
│       │   ├── agent/      # LangGraph orchestrator, rules.py, narrative
│       │   ├── api/        # routers
│       │   └── db/         # SQLAlchemy models
│       ├── tests/
│       └── requirements.txt
├── packages/
│   └── contract/          # generated TS types + Zod schemas
├── e2e/                   # Playwright, one spec per demo scenario
├── scripts/               # export-openapi.ts, dev up/down, seed-fixtures
└── specs/ (constitution.md, spec.md, plan.md, tasks.md)
```

**API surface**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/inspect` | multipart image upload, returns `run_id` |
| POST | `/api/monitor/start` | begin a monitor run |
| POST | `/api/monitor/frame` | live webcam frame |
| PUT | `/api/monitor/zone` | save the polygon danger zone |
| GET | `/api/runs/{id}/stream` | SSE progress |
| GET | `/api/runs/{id}` | run status |
| POST | `/api/runs/{id}/inputs` | submit manual inputs, resume the agent |
| GET | `/api/runs/{id}/report` | report |
| GET | `/api/runs?verdict=&limit=` | history, filterable |
| POST | `/api/runs/{id}/share` | create a read-only share link |
| GET | `/share/{token}` | public read-only report |

**Rule engine** — `agent/rules.py` computes the verdict. Severity rules are pure functions
`check_*(image) -> Finding`. The model receives a text-only summary, explains, and may only
escalate.

**Risk score** — `risk = min(100, Σ(weight[severity] × confidence))`, weights `{ok: 0,
warning: 0.4, critical: 1.0}`. Displayed as advisory; never alters the verdict.

**Confidence** — below 0.35 a check yields `warning`, never `ok`.

**Model instance purity** — a single module-level YOLO singleton, created on first use, so
loading is not per-frame; tools stay pure functions of their input.

**Agent graph** — five ordered steps (body, fins, launchpad, weather/manual, decision). Missing
mandatory inputs pause via `asyncio.Event` and resume on submission.

**Proposals on the plan**

1. **noisy-OR combination** — `1 − Π(1 − w_i·c_i)` instead of the saturating sum, to keep the
   score order-independent and bounded.
2. **rules out of `agent/`** — move the rule engine to a top-level `rule_engine/` so it can never
   import the agent or the CV code.
3. **POST rather than WebSocket** for webcam frames — unidirectional, so a socket adds lifecycle
   complexity for no gain; base64 avoided by posting raw JPEG.
4. **SSE fan-out** — an event bus keyed by `run_id` so multiple browser tabs stay consistent.
5. **startup recovery** — on boot, runs left `running` are reconciled from the LangGraph
   checkpointer; interrupted runs become `paused`, crashed runs become `failed`, and neither is
   ever resumed toward a verdict.
6. **event log persistence** — persist every SSE event with a monotonic per-run sequence so a
   reconnecting client can replay from `Last-Event-ID`.
7. **DecryptedText on the verdict badge** for a typewriter reveal of GO / HOLD / NO-GO.
8. **Turborepo** for the monorepo task graph.
9. **`.env.example`** — `OPENAI_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`; the key stays
   server-side and never `NEXT_PUBLIC_*`.
10. **EasyOCR** as a P2 add-on for fin alignment and zone markers.
11. **Next.js proxy** — the web app proxies `/api` to the API so the browser sees one origin;
    SSE must not be buffered by the proxy.
12. **Print / PDF** view of the report, plus the share link.

## Response snapshot

Completed `/sp.plan`: wrote `plan.md`, `research.md`, `data-model.md`, `contracts/api.md`,
`contracts/events.md`, and `quickstart.md`, then ran
`update-agent-context.ps1 -AgentType opencode`. All eleven Constitution Check gates pass after
design, with zero Complexity Tracking entries.

Fourteen research decisions were taken (R1–R14), each checked against current published
documentation rather than written from memory. Five changed the supplied plan:

1. **The pause is LangGraph's native `interrupt()`, not an `asyncio.Event`.** An `asyncio.Event`
   holds the pause in one process's memory, so an API restart would lose a run that the spec
   requires to remain retrievable in a paused state. `interrupt()` requires a checkpointer;
   `AsyncSqliteSaver` from `langgraph-checkpoint-sqlite` provides it, with `thread_id = run_id`.
   Two verified behaviours changed the node structure: **on resume the node restarts from the
   beginning**, so `interrupt()` must be the first statement in the `weather_manual` node and CV
   work must live in earlier nodes that never re-run; and invalid input is handled by returning
   `pending_question` in state and looping back over a conditional edge, which gives FR-023's
   inline validation with no hand-rolled retry.
2. **The risk score is verdict-banded and saturating, replacing the saturating sum.** A sum over
   findings grows with the number of findings, so a module emitting ten warnings outranked one
   genuine critical, and a run where every check degraded to `warning` scored ~88 while
   displaying `HOLD` — a gauge reading "nearly NO-GO" beside a HOLD badge is a communication
   failure in a safety tool. The replacement accumulates warning and critical evidence separately,
   saturates each against a fixed capacity, and places the result in the band its own verdict
   implies: GO 0–30, HOLD 40–69, NO-GO 70–100. A `low_confidence` accumulator stops a GO earned on
   shaky evidence from reading a reassuring zero. Band selection reuses the verdict predicate,
   which is permitted because the verdict is already a pure function of findings, so FR-003's
   "reproducible from findings alone" still holds.
3. **`DecryptedText` removed from the verdict badge.** UX-003 and Constitution 4.III both
   prohibit motion on the verdict badge. The badge is static text, icon, and colour. The
   remaining React Bits are `Threads`/`Aurora` (background), `Counter` (risk gauge), and
   `SpotlightCard` (card surface) — exactly the four permitted categories — installed from the
   free shadcn registry as `TS-TW` variants, each behind a `useReducedMotion()` guard that skips
   mounting rather than zeroing a duration. Verified: Pro components are a separate,
   license-gated registry and are out of scope.
4. **The rule engine is hoisted to `rule_engine/`, and it owns the decision types.** The
   dependency direction is one-way: `cv/` type-annotates its returns with `Finding` from
   `rule_engine.types`, and `agent/` imports the engine to call it. Making the `Finding` dataclass
   the same type the engine consumes is the strongest available form of Constitution 2.III — a
   finding missing module, check id, severity, message, confidence, or metrics does not
   type-check, so it cannot be admitted into a decision. The engine reaches no model by
   construction, not by discipline.
5. **`Finding.metrics` became a list of typed `Measurement` records.** The supplied `Finding` had
   a `metrics` map, which cannot express the requirement in FR-043 and SH-007 at all: a fin angle
   of 3.4° against a 3° threshold with ±1.5° of error is the entire problem, and it is
   unrepresentable in `dict[str, float]`. `Measurement{name, value, unit, error_margin, threshold}`
   plus a pure `is_threshold_ambiguous()` makes FR-043 satisfiable and drives the SH-007
   disclosure line.

The apparent conflict between Constitution 2.II and the spec's "a low-confidence person inside
the zone is still hold-or-worse" edge case was resolved by reading 2.II for what it is: a
**one-way floor that forbids `ok`**, not a cap that forces `warning`. A `critical` at 0.20
confidence therefore stays `critical` and the run is a NO-GO. This is the only reading consistent
with both documents, and it is written into `research.md` R8 so `/sp.analyze` can classify it as
resolved-by-construction rather than as a reinterpretation — which the constitution's Governance
section forbids. `MIN_CONFIDENCE_FOR_OK = 0.35` is pinned in `rule_engine/config.py` and served
from `GET /api/config`, satisfying the constitution's `TODO(CONFIDENCE_FLOOR)`. A `critical`
below the floor additionally carries `low_confidence_critical` and a "produced by the fail-safe
rule" note, which is the honesty requirement that case most needs.

Two further corrections the plan did not anticipate: every overlay coordinate is **normalized
0–1**, which makes FR-013 (re-render at any size) free, makes per-module overlay toggling a
render-time decision with no server round-trip, and makes FR-039's "no absolute pixel coordinates
in the LLM payload" structural rather than a filtering rule; and the narrative payload is built
from an explicit field **allow-list** rather than by serialising a `Run` and deleting fields, so
a future column cannot leak by default, with a unit test asserting the serialized payload matches
a denylist of `data:image`, `base64`, image MIME types, and absolute paths — which turns SH-009
from an aspiration into a check.

`@hey-api/openapi-ts` with the Zod v4 plugin was selected for R1 because it is the one tool that
generates types *and* Zod schemas in a single pass from one OpenAPI document, so the two halves
of Constitution 3.I cannot disagree. `packages/contract/src/` is generated and git-ignored, and
CI regenerates then runs `git diff --exit-code`, so a stale contract is a build failure.

One dependency-direction note worth flagging: the plan template's mandated tree places
`apps/api/{agent,cv,rule_engine,db}` as siblings, whereas the supplied plan nested `cv/` and
`agent/` inside `app/`. The siblings layout was used, because nesting detection inside the
transport package weakens the boundary Constitution 3.II exists to protect. Both sit under
`apps/api/`, so the template's three top-level directories are untouched.

`AGENTS.md` was regenerated by `update-agent-context.ps1`, which correctly extracted the language,
framework, and storage lines from the new `plan.md` but wrote the generic
`backend/ frontend/ tests/` tree and `cd src; pytest; ruff check .` — the exact
`TODO(TOOLING_LAYOUT)` limitation the constitution's Sync Impact Report predicted. Corrected
through the `MANUAL ADDITIONS` block, which survives regeneration: real directory tree, the real
commands with `--workers 1` marked REQUIRED, and a restatement of the seven non-negotiables.

## Outcome

- ✅ Impact: `/sp.plan` complete. `plan.md` filled with all nine Technical Context fields, the
  pre-research and post-design Constitution Check evaluations (11/11 pass, no Complexity Tracking
  entries), a Structure Decision table, and a Deterministic Decision Model recording the verdict
  order, the 0.35 confidence floor, the banded risk formula, and the ambiguity rule.
  `research.md` records 14 decisions with rationale and rejected alternatives. `data-model.md`
  defines 8 enumerations, 5 domain types, 8 SQLAlchemy tables, the run and step state machines,
  and a derivation table showing every decision value is a `rule_engine` output. `contracts/api.md`
  and `contracts/events.md` specify 17 endpoints with one error envelope and 8 SSE event types
  with full reconnect semantics. `quickstart.md` gives setup, run, verification, a judge
  walkthrough, a troubleshooting table, and the pre-PR merge gate.
  Five of the supplied plan's proposals were corrected: the `asyncio.Event` pause, the saturating
  sum, the verdict-badge animation, the unhoisted rule engine, and the untyped metrics map.
- 🧪 Tests: no executable code — this is a planning stage. Validation performed: three researched
  decisions verified against current vendor documentation rather than memory (`@hey-api/openapi-ts`
  Zod v4 plugin exists and auto-detects version; `interrupt()` requires a checkpointer, restarts
  the node on resume, and exposes `stream.interrupts`/`interrupted`/`output` on `version="v3"`;
  React Bits serves `{Name}-TS-TW` from `https://reactbits.dev/r/{name}.json` with Pro on a separate
  license-gated registry); two further assumptions verified (`langgraph-checkpoint-sqlite`'s
  `AsyncSqliteSaver` requires `aiosqlite` and **must be closed or the graph appears to hang** —
  hence the FastAPI lifespan hook; Next.js SSE needs `no-transform`, `X-Accel-Buffering: no`,
  stripped `Content-Length`, and `req.signal` teardown). All 11 gates re-checked against the
  finished design. Every cross-document link in the six artifacts resolves, and the two
  constitution TODOs raised by the specification — `SCOPE_LEDGER` and `CONFIDENCE_FLOOR` — are now
  both discharged.
- 📁 Files: `specs/001-launchguard-mvp/{plan,research,data-model,quickstart}.md`,
  `specs/001-launchguard-mvp/contracts/{api,events}.md`, `AGENTS.md`, this PHR.
- 🔁 Next prompts: `/sp.analyze` to cross-check spec ↔ plan ↔ constitution for drift, with the
  Constitution 2.II vs. low-confidence-person edge case (R8) and the risk formula's dependence on
  the verdict predicate (R7) as the two items most likely to be re-litigated. Then `/sp.tasks`.
  `/sp.tasks` must carry forward three things that are easy to lose: the `interrupt()`-first rule
  for the `weather_manual` node, the order-independence test for the YOLO singleton, and the
  SH-009 denylist test for the narrative payload.
- 🧠 Reflection: The most valuable thing Phase 0 did was refuse to write down two answers that felt
  obviously right. "Use `asyncio.Event` to pause the agent" is a perfectly reasonable-looking
  design that silently violates a spec edge case, and it was only caught by asking what happens
  to a paused run when the process restarts. "Saturate the weighted sum at 100" is likewise
  reasonable-looking and produces a risk gauge that contradicts the badge beside it. Neither was
  a hard problem; both were failures to check a claim against the requirement it was supposed to
  satisfy. The second habit worth keeping: the specification deferred three decisions to
  planning, and each of them — detector weights, narrative model, risk formula — turned out to be
  a place where the obvious choice was wrong in a way that mattered. Deferring them was what made
  the difference visible.

## Evaluation notes (flywheel)

- Failure modes observed: (1) `update-agent-context.ps1` reported "Created new opencode context
  file" for `AGENTS.md`, overwriting the existing one. Harmless in outcome — the old file was
  itself auto-generated and its `Project Structure` was the same wrong generic tree — but the
  script does not distinguish create from update, so a future run on a hand-maintained
  `AGENTS.md` would destroy manual work. The fix belongs in the `MANUAL ADDITIONS` block, which
  the script preserves, not in the file's generated section. This is the concrete content of the
  constitution's `TODO(TOOLING_LAYOUT)` follow-up. (2) The verbatim `/sp.plan` argument was not
  carried into this stage's context, so the Prompt section above is a faithful reconstruction
  rather than a transcript; it is labelled as such rather than presented as verbatim.
- Graders run and results (PASS/FAIL): PASS — all 9 Technical Context fields filled, none left as
  `NEEDS CLARIFICATION`; PASS — 11/11 Constitution Check gates pass post-design with zero
  Complexity Tracking entries; PASS — the three constitutionally-deferred decisions (detector
  weights, narrative model, risk formula) are all resolved and recorded in `plan.md`;
  PASS — `Finding` carries a representable measurement error margin, closing the PHR-0002
  prediction that FR-043 was the requirement most likely to be silently dropped; PASS — no
  React Bits component on the verdict badge, finding list, severity indicators, or disclaimer;
  PASS — `rule_engine/` imports nothing from `cv/` or `agent/`, and the dependency direction is
  stated in the plan; PASS — `MIN_CONFIDENCE_FOR_OK = 0.35` pinned in code and in `GET /api/config`,
  discharging `TODO(CONFIDENCE_FLOOR)`; PASS — the deferred list (thermal, drone, telemetry,
  digital twin, vibration, ground control) appears in no requirement, route, or string, and the
  story-3 colour-threshold cue detectors are explicitly distinguished from the deferred thermal
  work; PASS — no hand-written API types in `apps/web`; PASS — every document link resolves.
- Prompt variant (if applicable): baseline, immediately following PHR-0002 (spec stage) on the
  same feature thread.
- Next experiment (smallest change to try): run `/sp.analyze` and deliberately test whether the
  risk formula's reuse of the verdict predicate (R7) trips the "risk MUST NOT alter the verdict"
  requirement as a CRITICAL finding. The plan argues it cannot, because the score is never an
  input to the verdict and the verdict is already a pure function of findings — but an independent
  reviewer may reasonably read R7 as circular, and if it is found wanting, the fix is to drop the
  band and let the score float. Better to learn that here than during `/sp.tasks`.
