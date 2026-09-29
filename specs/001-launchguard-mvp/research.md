# Phase 0 Research: LaunchGuard AI MVP

**Feature**: `001-launchguard-mvp`
**Date**: 2026-09-29
**For plan**: `specs/001-launchguard-mvp/plan.md`
**Governing document**: `.specify/memory/constitution.md` v1.0.0

Every decision below was checked against the current published documentation, not from memory.
Each entry records the question, the decision, the rationale, and the alternatives that were
rejected with a reason, so that `/sp.tasks` does not have to re-litigate them.

---

## R1 — Contract generation: OpenAPI to TypeScript types and Zod schemas

**Question**: Constitution 3.I requires the contract in `packages/contract` to be *generated*
from the API's OpenAPI document into TypeScript types **and** Zod schemas. Which generator does
both in one pass?

**Decision**: `@hey-api/openapi-ts` with the built-in `zod` plugin, targeting Zod v4.

Configuration:

```ts
// packages/contract/openapi-ts.config.ts
import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: './openapi.json',
  output: { path: './src' },
  plugins: [
    '@hey-api/typescript',
    {
      name: 'zod',
      compatibilityVersion: 4, // default; auto-detects the installed zod version
      types: { infer: true },  // z.infer<typeof x> types from the Zod schemas
    },
  ],
});
```

**Rationale**

- Verified: the `zod` plugin emits a Zod schema for every reusable definition, every request
  layer, and every response layer, and supports `zod.infer` type inference — one generator
  covers both halves of the Constitution 3.I requirement, so types and validators can never
  disagree because they came from the same pass.
- `compatibilityVersion: 4` is the current default and the plugin warns on a mismatch against
  the installed `zod`, which turns a silent contract drift into a build error.
- Free, MIT-licensed, runs on Node 22+, and accepts a local file path as `input` — no registry
  account or hosted service is required, which matters for NFR-006 (single laptop, no external
  service dependency).

**Alternatives rejected**

| Alternative | Rejected because |
|---|---|
| `openapi-typescript` (the upstream predecessor) | Generates types only. Zod schemas would still have to be hand-written, reintroducing exactly the drift Constitution 3.I exists to prevent. |
| `orval` with its Zod plugin | Also does both, but pulls in a much larger plugin surface and is the heavier dependency for a two-deployable MVP. Kept as a fallback if the Zod v4 plugin regresses. |
| `openapi-zod-client` | Thin wrapper with a smaller feature set and less active maintenance. |
| Hand-writing Zod schemas in `apps/web` | Prohibited by Constitution 3.I. |

**Contract pipeline (2 steps, both offline)**

1. `python -m scripts.export_openapi` imports the FastAPI app and writes `openapi.json` by
   calling `app.openapi()`. Importing the app is deterministic and needs no running server, so
   the export cannot be polluted by request-time state.
2. `npx @hey-api/openapi-ts` generates `packages/contract/src/`.

`packages/contract/src/` is **generated and git-ignored**. A `pnpm generate` script runs both
steps and is wired as `prebuild` in `apps/web`. CI runs `generate` then `git diff --exit-code`
to prove the committed contract is not stale.

---

## R2 — Agent pause/resume: LangGraph interrupts

**Question**: The input plan described the manual-inputs pause as an "`interrupt` (asyncio Event)".
What is the correct LangGraph mechanism, and what does it force on the node structure?

**Decision**: Use the native `interrupt()` function with `Command(resume=...)` and a persistent
`AsyncSqliteSaver` checkpointer. Do **not** hand-roll an `asyncio.Event`.

**Rationale**

- Verified: `interrupt()` requires a checkpointer; state is persisted at the exact point of the
  call; the graph waits indefinitely; and the value passed as `Command(resume=...)` becomes the
  return value of `interrupt()` inside the node. An `asyncio.Event` would hold the pause only in
  the memory of one process, so an API restart would lose the run — violating the spec edge case
  "A run left mid-pause awaiting manual input, then abandoned — the run remains retrievable in
  history in a paused state".
- Verified: `stream_events(..., version="v3")` surfaces `stream.interrupts`, `stream.interrupted`
  and `stream.output`. That maps one-to-one onto the SSE events required by Constitution 3.IV,
  so the streaming transport is driven by the framework rather than hand-built around it.

**Two verified behaviours that change the design**

1. **On resume, the node restarts from the beginning of the node** — everything before the
   `interrupt()` call runs again. Consequence: the `check_manual_inputs` node MUST place
   `interrupt()` as its first statement, and every graph node that can be resumed must be
   idempotent with respect to side effects. Specifically, CV tool calls live in *earlier* nodes
   and are never re-executed, because resume restarts only the node that raised the interrupt.
2. **Retrying invalid input**: call `interrupt()` exactly once per node invocation; on invalid
   input return the updated `pending_question` in state and use a conditional edge to loop back
   to the same node. This gives FR-023 (inline validation, no duplicate prompts) without a
   hand-rolled retry loop.

**Checkpointer**: `AsyncSqliteSaver` from the `langgraph-checkpoint-sqlite` package
(`pip install langgraph-checkpoint-sqlite aiosqlite`; import from
`langgraph.checkpoint.sqlite.aio`). The synchronous `SqliteSaver` is explicitly documented as not
scaling to multiple threads and is therefore not used by an async FastAPI app.

Verified caveat that must be handled: **the checkpoint connection must be closed or the graph
appears to hang.** It is opened in the FastAPI `lifespan` startup hook and closed in the
corresponding shutdown hook.

`thread_id` is the `run_id`, so a run's graph state and its database row are addressed by the
same key.

---

## R3 — React Bits: component names, install path, and the atmosphere boundary

**Question**: The input plan named several React Bits components. What are the real names and
install commands, and which may appear on the decision path?

**Decision**: Install from the free shadcn registry with the `TS-TW` variant suffix:

```bash
# Register the registry once, in components.json
#   "registries": { "@react-bits": "https://reactbits.dev/r/{name}.json" }
npx shadcn@latest add @react-bits/Aurora-TS-TW
npx shadcn@latest add @react-bits/Counter-TS-TW
npx shadcn@latest add @react-bits/SpotlightCard-TS-TW
npx shadcn@latest add @react-bits/Threads-TS-TW
```

Each component ships in four variants — `{Name}-JS-CSS`, `{Name}-JS-TW`, `{Name}-TS-CSS`,
`{Name}-TS-TW` — served from `https://reactbits.dev/r/{name}.json`. Because the stack is
TypeScript strict with Tailwind, `TS-TW` is the only variant used.

**Rationale for the component selection.** Constitution 4.III confines React Bits to
"background effects, hero text, counters, and spotlight cards". The four chosen above map
exactly onto that list: `Threads`/`Aurora` for the background, `Counter` for the risk score
(the one explicitly permitted motion target in UX-003), and `SpotlightCard` for card surfaces.

**`DecryptedText` is removed from the verdict badge.** The input plan used it to animate the
GO / HOLD / NO-GO decision badge. UX-003 and Constitution 4.III both prohibit motion on the
verdict badge, the finding list, severity indicators, and the disclaimer. The badge is static
text + icon + colour, permanently. This is a correction to the input plan, not a preference.

**Verified constraint**: Pro components live in a **separate, license-gated registry** and cannot
be installed from the free one. Any Pro component is out of scope for this repository.

**Accessibility wiring**: every `components/react-bits/*` component is rendered behind a
`useReducedMotion()` guard from `motion/react`; when the user prefers reduced motion the
component is not mounted at all rather than mounted with a zero duration.

---

## R4 — Webcam transport

**Question**: WebSocket, MJPEG, or HTTP POST per frame?

**Decision**: `POST /api/monitor/{run_id}/frame` with a raw `image/jpeg` body, one frame in
flight at a time, enforced client-side by skipping a capture while a request is outstanding.

**Rationale**

- The channel is unidirectional — frame in, findings plus zone status out. A WebSocket adds
  reconnection, heartbeat and backpressure lifecycle code to a single-machine MVP for no gain.
- Raw JPEG avoids the ~33% size overhead of base64-in-JSON, which matters when the target is
  2 analysed frames per second on a laptop CPU (FR-015, NFR-002).
- Single-in-flight gives natural backpressure: if a frame takes 400 ms, the client captures at
  2.5 fps rather than queueing frames the server will process after the user has moved on. A
  queue would inflate end-to-end latency and break SC-003.

**Alternatives rejected**

| Alternative | Rejected because |
|---|---|
| WebSocket | Bidirectional lifecycle, reconnection and backpressure code for a unidirectional channel. |
| Base64 frame inside a JSON body | ~33% bandwidth overhead and an avoidable decode step on the hot path. |
| MJPEG `multipart/x-mixed-replace` | Cannot attach a per-frame result, so the zone status and finding overlays could not be driven from server output. |
| Server-pulls from the camera | Breaks FR-040's browser-only camera model and reintroduces browser-side media handling. |

---

## R5 — SSE fan-out, reconnect, and the Next.js proxy

**Question**: The spec requires two browser tabs on one run to stay consistent (Concurrency edge
case) and requires progress to stream live (Constitution 3.IV). How is the event stream fanned
out and survive a reconnect?

**Decision**: A persisted event log plus an in-process pub/sub.

- Every emitted event is appended to a `run_events` table with a monotonic per-run `seq`.
- An in-process `asyncio` pub/sub keyed by `run_id` fans each event out to all live subscribers.
- Each SSE frame carries `id: <seq>`, so a reconnecting client sends `Last-Event-ID` and the
  server replays everything after that sequence from the database before re-attaching live.
- A `:heartbeat` comment every 15 s keeps intermediaries from closing an idle connection.

This design is what makes the two-tab case and the mid-stream reconnect fall out for free rather
than needing separate code paths.

**Explicitly accepted limitation**: in-process pub/sub assumes **one API worker process**
(`uvicorn --workers 1`). This is consistent with NFR-006 and spec Assumption 11 (single-operator,
single-machine deployment) and is documented in `quickstart.md` rather than left as a surprise.
A multi-worker deployment would need a broker (Redis pub/sub) or a Postgres `LISTEN/NOTIFY`.

**Next.js proxy**: a catch-all Route Handler at `apps/web/app/api/[...path]/route.ts` that
pipes the upstream body straight through, with:

```ts
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// response headers on the SSE path:
'Content-Type': 'text/event-stream; charset=utf-8',
'Cache-Control': 'no-cache, no-transform',
Connection: 'keep-alive',
'X-Accel-Buffering': 'no',
```

`no-transform` prevents compression middleware from buffering, `X-Accel-Buffering: no` covers a
future nginx hop, and the `Content-Length` header is stripped from the upstream response so the
transfer stays chunked. The handler also listens on `req.signal` to unsubscribe the pub/sub
client when the tab closes, otherwise each closed tab would leak a queue.

**Rejected alternative**: `next.config.ts` rewrites for the `/api` prefix. Simpler, but a
rewrite cannot be guaranteed not to buffer the event stream, and the failure mode — a spinner
that never resolves — is exactly the "single opaque spinner" that Constitution 3.IV exists to
eliminate. A Route Handler is used instead so the streaming behaviour is owned and testable.

---

## R6 — Rule engine isolation and dependency direction

**Question**: The plan template mandates `apps/api/rule_engine/`. Where do the decision types
live, and what may the rule engine import?

**Decision**: `rule_engine/` owns the canonical decision types and imports **nothing** from
`cv/` or `agent/`. The dependency direction is one-way:

```text
cv/  ──imports types──>  rule_engine/  <──imports──  agent/
                            │
                            └── imports nothing from cv/ or agent/
```

`rule_engine/types.py` defines `Severity`, `Verdict`, `Measurement`, `Finding`, `Thresholds`,
`ManualInputSet` and `Decision`. `cv/` type-annotates its return values with `Finding` from
`rule_engine.types`; `agent/` imports the engine to call it.

**Rationale**: making the `Finding` dataclass the *same* type the decision consumes is the
strongest available form of Constitution 2.III. A finding that cannot carry module, check id,
severity, message, confidence and metrics does not type-check as a `Finding`, so it cannot be
"admitted into a decision" by accident. Keeping the direction `cv → rule_engine` also means the
rule engine has no reachable path back to detection code, so the verdict cannot become a function
of a model.

**Resulting checklist registry** — 15 stable check ids, five ordered steps, matching FR-021:

| Step | Check ids |
|---|---|
| 1 body | `body.cracks`, `body.dents`, `body.damage`, `body.burn_marks`, `body.missing_parts` |
| 2 fins | `fin.alignment` |
| 3 launchpad area | `zone.occupancy`, `cue.smoke`, `cue.fire`, `cue.leak`, `cue.motion` |
| 4 weather + manual | `manual.wind`, `manual.visibility`, `manual.precipitation`, `manual.area_cleared` |
| 5 decision | — (produces the verdict; emits no findings) |

The four cue checks are attached to step 3 because they describe the pad and vehicle base during
monitoring, which is where Story 3's cues originate.

---

## R7 — Risk score formula

**Question**: FR-003 requires an integer 0–100 derived from finding severities weighted by
confidence, advisory only. The input plan used `min(100, Σ weight × confidence)`. What replaces it?

**Decision**: A **verdict-banded, saturating** score with two evidence accumulators.

```text
warning_evidence  = Σ over warning findings  of (0.25 × confidence)   # capacity 2.0
critical_evidence = Σ over critical findings of (1.00 × confidence)   # capacity 3.0
low_confidence   = Σ over ok findings where 0 < confidence < 0.35 of (0.35 − confidence)

GO     → round(100 × min(0.30, low_confidence / 0.60))                  # band 0–30
HOLD   → round(40 + 29 × min(1.0, warning_evidence / 2.0))              # band 40–69
NO-GO  → round(70 + 30 × min(1.0, critical_evidence / 3.0))             # band 70–100
```

Band selection reuses the verdict predicate itself. This is permitted because the verdict is
already a pure function of findings and manual-input rule results, so the score remains
reproducible from findings alone as FR-003 and spec Assumption 4 require.

**Rationale — three properties the rejected formula lacked**

1. **Order independence and no runaway accumulation.** A sum over findings grows with the
   number of findings, so a module emitting ten warnings outranked a single genuine critical.
   `min(1.0, evidence / capacity)` saturates, so a run cannot be pushed to 100 by repetition, and
   the result does not depend on the order findings arrive in.
2. **Internal consistency with the badge.** The gauge sits next to the verdict. With the
   saturating-only formula, a run whose every check degraded to `warning` scored ~88 while
   displaying `HOLD` — a gauge reading "nearly NO-GO" next to a HOLD badge is a communication
   failure in a safety tool. Banding makes a GO never read above 30, a HOLD never read above 69,
   and a NO-GO never read below 70.
3. **Honesty about weak evidence.** `low_confidence` is why a GO is not forced to 0. A GO
   earned on shaky detections reads in the upper part of the GO band instead of a reassuring
   zero, which is the behaviour Constitution 2.IV asks for.

**Why the verdict cannot be laundered upward by the score**: the score is a pure output of the
engine, it is never an input to the verdict, and no test path exists for score to influence
severity. FR-003 and Constitution 2.I are satisfied by construction, and
`rule_engine/tests/test_risk_score.py` asserts the bands for every severity combination.

**Known and accepted**: a single critical at the 0.35 confidence floor scores 74, not 100. This
is intentional — the score expresses certainty, while the verdict expresses consequence. The
report states the verdict and the score as separate lines for this reason.

---

## R8 — Low-confidence threshold

**Question**: Constitution 2.II requires a "documented low-confidence threshold" and leaves the
numeric value deliberately unset (`TODO(CONFIDENCE_FLOOR)` in the constitution's Sync Impact
Report). What value, and how does it interact with the spec's person-in-zone rule?

**Decision**: `MIN_CONFIDENCE_FOR_OK = 0.35`, defined once in `rule_engine/config.py` and
surfaced in `GET /api/config` so the UI can display it.

The floor is applied as a **one-way floor, never a downgrade**:

```python
def apply_confidence_floor(severity: Severity, confidence: float) -> Severity:
    if confidence < MIN_CONFIDENCE_FOR_OK and severity is Severity.OK:
        return Severity.WARNING
    return severity   # warning and critical are never reduced
```

**Resolving the apparent conflict between Constitution 2.II and the spec edge case.** The
constitution says a low-confidence result yields `warning` and must not yield `ok`. The spec says
a low-confidence person inside the danger zone is still a hold-or-worse condition, never `ok`.
These are consistent once the constitution's rule is read for what it is: a *floor that forbids
`ok`*, not a cap that forces `warning`. A `critical` finding produced by the zone rule at 0.20
confidence therefore stays `critical`, and the run is not a NO-GO. This reading is the only one
that satisfies both documents, and it is recorded here because
`/sp.analyze` must classify the interaction as resolved-by-construction rather than reinterpreted.

**Honesty additions required by this decision**

- A module that errors, times out, or is skipped emits `severity="warning"`, `confidence=0.0`,
  and `degraded=true`, with a message naming the failure. It is never `ok` (FR-005).
- A `critical` finding whose confidence is below 0.35 additionally carries
  `low_confidence_critical=true`, and the report adds: *"Low detection confidence — this verdict
  is conservative and was produced by the fail-safe rule."* This keeps FR-038 and SH-005
  satisfied for exactly the case that is most likely to be over-claimed.
- 0.35 is a **starting value to be validated against the reference fixture set** in
  `/sp.tasks`, not a measured optimum. The constitution requires it pinned in code and in the
  API config; both are done here.

---

## R9 — Measurement error margin (FR-043)

**Question**: FR-043 and SH-007 require a measurement to carry its error margin when it falls
within that margin of a decision threshold. `Finding` as described in the spec's Key Entities has
metrics but no defined uncertainty representation.

**Decision**: metrics are not a free-form map. They are a list of typed `Measurement` records:

```python
@dataclass(frozen=True)
class Measurement:
    name: str
    value: float
    unit: str
    error_margin: float | None = None
    threshold: float | None = None
```

A single pure helper computes ambiguity:

```python
def is_threshold_ambiguous(m: Measurement) -> bool:
    return (
        m.threshold is not None
        and m.error_margin is not None
        and abs(m.value - m.threshold) <= m.error_margin
    )
```

When it is true, the finding carries `near_threshold_note` and the report renders the
ambiguity line required by SH-007. The fin-alignment module declares `error_margin=1.5` degrees,
matching SC-002's stated accuracy of 1.5°.

**Rationale**: this is the only way FR-043 is satisfiable at all. A bare `metrics` map cannot
express "this number is 3.4° and the threshold is 3° and my error is ±1.5°", which is the entire
requirement. The spec's own edge case ("a defect near the warning threshold may be reported as
`ok`. This margin is accepted for the MVP") is only *honest* if the report discloses it.

**Consequence on thresholds, stated in the report**: FR-011 and FR-029 keep the boundary on the
less-severe side (strictly greater-than), as the spec requires, and the disclosure is the
mitigation. Unchanged by this plan.

---

## R10 — Stateless CV with a lazily created model singleton

**Question**: Constitution 3.III requires CV functions to be pure `(input) -> Finding`, while
NFR-002 requires a frame under 500 ms. Re-initialising YOLOv8n per frame would blow the budget.
How are both satisfied?

**Decision**: A single lazily-created module-level model instance, created on first use, guarded
by a `threading.Lock`, and returned by an `lru_cache`d accessor. `predict()` receives a freshly
decoded `np.ndarray` on every call and stores nothing per-request.

The distinction that makes this compliant: the singleton holds **weights**, not request state.
A second detector instance, a per-run configuration, or a "current frame" field would be a
violation; the model weights are not.

**Verification required in `/sp.tasks`**: calling the detector on fixture A and then fixture B in
one process must produce a result for B byte-identical to a fresh process's result for B. That
test is what turns the claim into a checked property, and it is the test that would catch a
regression of this decision.

Model choice: `yolov8n` (the smallest YOLOv8 checkpoint), CPU inference, `imgsz=640`, `conf`
and `iou` supplied from `Thresholds` so the detector stays swappable without touching the rule
engine or the contract (spec Assumption 2).

---

## R11 — Narrative generation and the no-image-bytes guarantee

**Question**: FR-039, SH-009 and Constitution 5.III forbid image data reaching any third party,
while FR-026 requires graceful degradation when the model is unavailable.

**Decision**

- A dedicated `NarrativeContext` DTO is assembled from findings **and nothing else**. It is
  built by an explicit allow-list of fields, not by serialising a `Run` and deleting fields, so
  a future column cannot leak by default.
- Excluded by construction: image bytes, base64 and data URIs, absolute pixel coordinates,
  bounding boxes, file paths, filenames, and the stored image itself. Only check ids, severities,
  confidence, human-readable messages, metric names, values, units and the risk score are sent.
- A unit test serialises the payload and asserts it matches a denylist of
  `data:image`, `base64`, `image/jpeg`, `image/png`, and any absolute filesystem path, and
  asserts it contains no run-local image reference. This is the test that makes SH-009
  verifiable rather than aspirational.
- Model: `gpt-4o-mini`, invoked only **after** the verdict is persisted, with a 6-second timeout
  and at most one retry. On timeout, error, or absence of `OPENAI_API_KEY`, the report renders
  from the template path with `narrative.status = "unavailable"` (FR-026, SH-008).
- The LLM response is parsed into `{ narrative, recommended_actions[] }` and validated. The
  verdict, risk score, checklist and ordered reasons are **not** part of the model's output
  schema at all, so there is no field it could write a verdict into (FR-025, Constitution 2.I).
- `run.completed` is emitted as soon as the verdict is fixed, carrying
  `narrative.status = "pending"`. A later `report.narrative_ready` event delivers the prose. The
  verdict therefore appears within NFR-001's 5 seconds regardless of model latency.

**Rejected alternative**: returning the whole report in one request after the narrative call.
Simpler, but it makes the UI's time-to-verdict hostage to the model, and it produces a spinner
rather than a streamed decision — directly against Constitution 3.IV.

---

## R12 — Startup recovery for interrupted runs

**Question**: Spec edge case — a run abandoned mid-pause must remain retrievable in a paused
state. What happens to runs that were `running` when the process died?

**Decision**: A FastAPI `lifespan` startup hook reconciles every run left in `running`:

1. Read LangGraph state for `thread_id == run_id`.
2. Interrupted → set lifecycle to `paused` and emit `run.awaiting_input` on next connect.
3. Not interrupted (crashed mid-step) → set lifecycle to `failed` with
   `reason = "interrupted_by_restart"`. **Never resumed toward a verdict.**

**Rationale**: a crashed run has partial findings. Re-deriving a verdict from them could produce
a `GO` from an incomplete inspection, which Constitution 2.II forbids in spirit and SH-001
forbids in letter. Failing closed is the only defensible behaviour, and it matches NFR-003's
"the run MUST always reach a verdict" in the weaker sense of "never hangs or crashes" — a
`failed` run carries an explicit reason, not a silent absence.

---

## R13 — Toolchain, and one explicit omission

**Decision**

- **pnpm workspaces**, npm 10-compatible lockfile. One `pnpm-workspace.yaml` covering `apps/*`
  and `packages/*`.
- **No Turborepo.** The repository has two deployables and one contract package; a task graph
  runner buys cache reuse that a three-package workspace does not need during a time-boxed
  hackathon, and it adds a config file that would itself need constitution review. `pnpm -r run
  <script>` and `prebuild` hooks cover the orchestration this project actually needs.
- **Turbopack** in dev, **ESLint 9 flat config** + **Prettier** for `apps/web`; **Ruff** +
  **mypy --strict`** for `apps/api` (Constitution 5.I).
- **mypy `--strict`** rather than default: the rule engine is the one component where a
  permissive type check is a safety risk rather than a style issue.

---

## R14 — Fixture set shape

**Decision**: fixtures are real JPEG/PNG files under `apps/api/tests/fixtures/images/`, named
`{check_id}__pass.{ext}` / `{check_id}__fail.{ext}`, with the demo-scenario fixtures being the
canonical pass and fail members of the three demo scenarios. Every CV module gets at least one
of each (Constitution 5.II), and each demo scenario gets a Playwright spec asserting its expected
verdict (SH-010).

**Rationale**: a `pass` fixture for `fin.alignment` is the Normal scenario's rocket; its `fail`
counterpart is the Misaligned fin scenario's rocket. Tying the demo assets to the test assets
means the thing the judges see is the thing the CI verified — which is what FR-036 and SH-010 are
actually asking for.

---

## Open items carried into `/sp.tasks`

| Item | Why it is not resolved here |
|---|---|
| Validating `MIN_CONFIDENCE_FOR_OK = 0.35` against fixtures | Requires running the detector; produces a tuning task, not a plan decision. The value is pinned in code and in the API config as Constitution 2.II requires. |
| Confirming the exact degraded-module confidence per module | Depends on per-module behaviour once implemented. The floor applies uniformly at 0.0. |
| Share-token lifetime and rotation | Spec Assumption 8 fixes the capability-link model and defers expiry; the MVP issues a non-expiring random token and records it on the report. No rotation until runs can be deleted. |
