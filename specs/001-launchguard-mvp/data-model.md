# Data Model: LaunchGuard AI MVP

**Feature**: `001-launchguard-mvp` | **Date**: 2026-09-29
**Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)
**Constitution**: `.specify/memory/constitution.md` v1.0.0

Two representations are specified below and they are not interchangeable:

1. **Domain types** (`apps/api/rule_engine/types.py`) — the frozen dataclasses the rule engine
   consumes. These are the *decision* shape. A `Finding` that lacks any required field does not
   type-check, so it cannot enter a decision (Constitution 2.III).
2. **Persistence models** (`apps/api/db/models.py`) — the SQLAlchemy tables. These are the
   *storage* shape, and may be reorganised without touching CV, agent, or rule-engine code
   (Constitution 3.V).

The OpenAPI document is generated from layer 1 and 3, never authored. See
[contracts/](./contracts/).

---

## 1. Enumerations

All enumerations are closed sets. `Severity` and `Verdict` admit no other value (FR-002).

```python
class Severity(StrEnum):
    OK       = "ok"
    WARNING  = "warning"
    CRITICAL = "critical"

class Verdict(StrEnum):
    GO    = "GO"
    HOLD  = "HOLD"
    NO_GO = "NO-GO"

class RunMode(StrEnum):
    INSPECTION = "inspection"   # Pre-Launch Inspection
    MONITOR    = "monitor"      # Launchpad Monitor
    DEMO       = "demo"         # Demo Mode, real pipeline (FR-036)

class RunStatus(StrEnum):
    RUNNING    = "running"
    PAUSED     = "paused"       # awaiting manual input, graph interrupted
    COMPLETED  = "completed"
    FAILED     = "failed"       # includes interrupted_by_restart (R12)

class SourceType(StrEnum):
    IMAGE_UPLOAD = "image_upload"
    VIDEO_UPLOAD = "video_upload"
    LIVE_STREAM  = "live_stream"
    DEMO_BUNDLE  = "demo_bundle"

class StepStatus(StrEnum):
    PENDING  = "pending"
    RUNNING  = "running"
    PASSED   = "passed"
    FAILED   = "failed"
    BLOCKED  = "blocked"        # awaiting manual input

class NarrativeStatus(StrEnum):
    PENDING     = "pending"
    AVAILABLE   = "available"
    UNAVAILABLE = "unavailable" # template path rendered (FR-026, SH-008)

class OverlayKind(StrEnum):
    BBOX     = "bbox"
    POLYLINE = "polyline"
    POLYGON  = "polygon"
    ARC      = "arc"            # fin angle deviation
    POINT    = "point"
```

### Checklist step registry (R6)

Five ordered steps, fifteen stable check ids. `step_key` and `position` are both stored so the
report can render the checklist in FR-021's exact order without a join.

| position | step_key | check ids |
|---|---|---|
| 1 | `body` | `body.cracks`, `body.dents`, `body.damage`, `body.burn_marks`, `body.missing_parts` |
| 2 | `fins` | `fin.alignment` |
| 3 | `launchpad_area` | `zone.occupancy`, `cue.smoke`, `cue.fire`, `cue.leak`, `cue.motion` |
| 4 | `weather_manual` | `manual.wind`, `manual.visibility`, `manual.precipitation`, `manual.area_cleared` |
| 5 | `decision` | — (emits the verdict, produces no findings) |

---

## 2. Domain types

### `Measurement` — makes FR-043 satisfiable

```python
@dataclass(frozen=True)
class Measurement:
    name: str                                   # e.g. "fin_angle_deviation"
    value: float
    unit: str                                   # e.g. "deg", "m/s"
    error_margin: float | None = None           # e.g. 1.5
    threshold: float | None = None              # the threshold it was compared against
```

`is_threshold_ambiguous(m)` returns `True` when `threshold` and `error_margin` are both set and
`abs(value - threshold) <= error_margin`. When true, the finding gains a `near_threshold_note`
and the report states the outcome is not distinguishable from the adjacent severity
(FR-043, SH-007). A bare metric map could not express this, which is why `Finding.metrics` is a
list of these records rather than a `dict[str, float]` (R9).

### `Overlay` — normalized geometry, never pixels

```python
@dataclass(frozen=True)
class Overlay:
    kind: OverlayKind
    check_id: str
    points: tuple[tuple[float, float], ...] = ()   # 0–1 normalized
    radius: float | None = None                    # for ARC, 0–1 normalized
    start_deg: float | None = None                 # for ARC
    end_deg: float | None = None                   # for ARC
    label: str | None = None
```

Every coordinate is normalized 0–1, for three reasons: the same overlay re-renders correctly at
any display size (FR-013); a single shape works for images, video, and live frames of differing
dimensions; and **no absolute pixel coordinate can reach the narrative payload**, which makes
FR-039's exclusion structural instead of a filtering rule. The client draws these as SVG, which
is also what makes per-module overlay toggling (FR-010) a render-time decision with no server
round-trip.

### `Finding`

```python
@dataclass(frozen=True)
class Finding:
    module: str                    # e.g. "cv.fins" | "rule_engine.manual"
    check_id: str                  # from the 15-id registry
    severity: Severity
    message: str                   # hedged: "appears", "possible" (FR-038)
    confidence: float              # 0.0 – 1.0
    metrics: tuple[Measurement, ...] = ()
    overlay: Overlay | None = None
    step_position: int = 0         # which checklist step produced it
    degraded: bool = False         # module errored / timed out / was skipped
    low_confidence_critical: bool = False
    near_threshold_note: str | None = None
```

**Required-field invariant** (Constitution 2.III). A finding is admissible into a decision only
when `module`, `check_id`, `severity`, `message`, and `confidence` are all present, and
`metrics` is non-empty. `validate_finding()` raises `InadmissibleFinding` otherwise, and the
rule engine calls it on every finding it receives. Pydantic additionally enforces
`0.0 <= confidence <= 1.0` at the API boundary.

**Overlay exception.** `zone.occupancy` and the four `manual.*` rules carry `metrics` but
`overlay = None`, because they describe a region or a scalar rather than an object box. This
matches the specification's own Constitution Alignment block and is the only permitted absence.

### `Thresholds` — all configurable without code changes (FR-004)

```python
@dataclass(frozen=True)
class Thresholds:
    fin_angle_warning_deg: float = 3.0
    fin_angle_critical_deg: float = 6.0
    fin_angle_error_margin_deg: float = 1.5    # SC-002
    wind_warning_ms: float = 10.0
    wind_critical_ms: float = 15.0
    poor_visibility_severity: Severity = Severity.WARNING
    heavy_precipitation_severity: Severity = Severity.WARNING
    area_not_cleared_severity: Severity = Severity.CRITICAL
    object_in_zone_severity: Severity = Severity.CRITICAL   # configurable down to warning (FR-014)
    motion_sensitivity: float = 0.5
    detector_conf: float = 0.25          # YOLO pre-filter, below the 0.35 OK floor
    detector_iou: float = 0.45
    zone_occupancy: bool = True
```

Stored per run as JSON in `runs.thresholds_json`, so a run is reproducible from its own record
rather than from whatever the config file says today. A run created with default thresholds is
indistinguishable from one created with the defaults copied in — which is what makes SC-001
"reproducible on a cold start" true.

### `ManualInputSet`

```python
@dataclass(frozen=True)
class ManualInputSet:
    wind_speed_ms: float | None = None              # >= 0, rejected inline if negative (FR-023)
    visibility: Literal["good", "moderate", "poor"] | None = None
    precipitation: Literal["none", "light", "heavy"] | None = None
    area_cleared: bool | None = None
    notes: str | None = None                        # optional, never mandatory (FR-030)
```

`MANDATORY_FIELDS = ("wind_speed_ms", "visibility", "precipitation", "area_cleared")`. Any
`None` among them → `HOLD`, each named in the reasons (FR-006, FR-030).

### `Decision`

```python
@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    risk_score: int                 # 0–100, advisory
    findings: tuple[Finding, ...]
    checklist: tuple[StepResult, ...]
    reasons: tuple[Reason, ...]     # ordered, critical first then warning, then by step
    missing_inputs: tuple[str, ...] # names every absent mandatory input
    computed_at: datetime
```

`reasons` is derived, not authored: every `warning` and `critical` finding becomes a reason,
ordered by severity then checklist position. The LLM receives this list and may reword it; it
may not add, drop, or reorder a reason (Constitution 2.V, FR-025).

---

## 3. Persistence models

SQLAlchemy 2 declarative, `Mapped[...]` annotations, `mypy --strict` clean. All timestamps are
timezone-aware UTC. All ids are UUIDv4 strings, generated in the application layer so they can
also be minted by a demo seed script without a database round-trip.

### `runs`

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | UUIDv4 |
| `mode` | `Enum(RunMode)` | |
| `source_type` | `Enum(SourceType)` | |
| `source_ref` | `String(512)` nullable | relative path under the local media dir; **never an absolute path** |
| `status` | `Enum(RunStatus)` | default `running` |
| `status_reason` | `String(200)` nullable | e.g. `interrupted_by_restart` |
| `verdict` | `Enum(Verdict)` nullable | null until step 5 completes |
| `risk_score` | `SmallInteger` nullable | 0–100 |
| `thresholds_json` | `JSON` | snapshot of `Thresholds` at creation |
| `frame_width` / `frame_height` | `Integer` nullable | source dimensions the zone was defined against |
| `created_at` / `started_at` / `updated_at` / `completed_at` | `DateTime(tz)` | |

Index: `(status)`, `(created_at desc)` for the dashboard and history list.

`source_ref` is stored relative because NFR-005 and FR-040 require local-only storage and the
narrative payload builder enumerates allowed fields — an absolute path is excluded by
construction, and so is a value that would reconstruct one.

### `findings`

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `run_id` | `String(36)` FK → `runs.id` | `ondelete="CASCADE"`, indexed |
| `seq` | `Integer` | emission order within the run, so replay is deterministic |
| `module` | `String(64)` | |
| `check_id` | `String(64)` | from the 15-id registry |
| `severity` | `Enum(Severity)` | |
| `message` | `Text` | hedged copy |
| `confidence` | `Float` | check constraint `0.0 <= confidence <= 1.0` |
| `metrics_json` | `JSON` | `Measurement[]` |
| `overlay_json` | `JSON` nullable | `Overlay`, normalized coordinates |
| `step_position` | `SmallInteger` | 0–5 |
| `degraded` | `Boolean` | default false |
| `low_confidence_critical` | `Boolean` | default false |
| `near_threshold_note` | `Text` nullable | |
| `created_at` | `DateTime(tz)` | |

Check constraint enforcing `confidence BETWEEN 0.0 AND 1.0` — the same bound the dataclass and
Pydantic enforce, restated at the storage layer so a bad write fails at the database too.

### `danger_zones`

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `run_id` | `String(36)` FK | unique per run — one zone per run in the MVP |
| `points_json` | `JSON` | ≥ 3 points, each `[x, y]` in 0–1 |
| `source_width` / `source_height` | `Integer` | frame the polygon was defined against (FR-012) |
| `label` | `String(80)` nullable | |
| `created_at` / `updated_at` | `DateTime(tz)` | |

Validation (spec edge case): fewer than three points, a self-intersecting polygon, or a
degenerate (zero-area) polygon is rejected with a message naming the specific problem.

### `checklist_steps`

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `run_id` | `String(36)` FK | |
| `position` | `SmallInteger` | 1–5 |
| `step_key` | `String(32)` | from the registry |
| `status` | `Enum(StepStatus)` | |
| `finding_ids_json` | `JSON` | ordered ids produced by this step |
| `required_inputs_json` | `JSON` | manual fields this step needs (step 4 only) |
| `started_at` / `finished_at` | `DateTime(tz)` nullable | |

Unique constraint on `(run_id, position)`. A run has exactly one row per step, created when the
run starts, so the checklist is renderable while it is still running.

### `manual_inputs`

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `run_id` | `String(36)` FK | |
| `field` | `String(32)` | one of the five FR-028 fields |
| `value_json` | `JSON` | typed per field |
| `rule_fired` | `Enum(Severity)` nullable | which threshold fired, if any |
| `captured_at` | `DateTime(tz)` | |

One row per field, upserted on resubmission so a corrected value replaces rather than appends.
`notes` is stored but never produces a `rule_fired`.

### `run_events`

| column | type | notes |
|---|---|---|
| `id` | `Integer` PK autoincrement | |
| `run_id` | `String(36)` FK | indexed |
| `seq` | `Integer` | monotonic per run, 1-based — the SSE `id:` |
| `event_type` | `String(48)` | see [contracts/events.md](./contracts/events.md) |
| `payload_json` | `JSON` | |
| `created_at` | `DateTime(tz)` | |

Unique constraint on `(run_id, seq)`. This table is what makes reconnect, two-tab consistency,
and post-restart replay work with no extra infrastructure (R5). A client reconnecting with
`Last-Event-ID: 37` receives every event with `seq > 37` before the live subscription attaches.

### `reports`

| column | type | notes |
|---|---|---|
| `id` | `String(36)` PK | |
| `run_id` | `String(36)` FK | **unique** — one report per run |
| `verdict` | `Enum(Verdict)` | denormalised from the run, byte-identical (SH-006) |
| `risk_score` | `SmallInteger` | denormalised |
| `reasons_json` | `JSON` | ordered, produced by the rule engine |
| `checklist_json` | `JSON` | pass/fail per step (FR-024) |
| `recommended_actions_json` | `JSON` | rule-derived defaults, always present |
| `narrative_status` | `Enum(NarrativeStatus)` | |
| `narrative_text` | `Text` nullable | null when status is `unavailable` (FR-026) |
| `narrative_model` | `String(64)` nullable | which model produced it, for audit |
| `disclaimer` | `String(200)` | the mandated text, stored so a report renders identically offline |
| `share_token` | `String(43)` nullable unique | `secrets.token_urlsafe(32)` (FR-033) |
| `annotated_ref` | `String(512)` nullable | relative path to the server-rendered composite |
| `generated_at` | `DateTime(tz)` | |

`reasons_json` and `checklist_json` are populated from the `Decision` **before** the narrative
step runs, and the row is written with `narrative_status = 'pending'`. The narrative update is
therefore an `UPDATE` to a narrative field only, which is how a model timeout or a missing API key
cannot affect the verdict, the risk score, the checklist, or the reasons (FR-026, SH-006, SH-008).

`disclaimer` is stored on the row rather than only in the frontend so a shared link, a print view,
and the live screen all render the identical mandated string (FR-037, SH-004).

### `demo_scenarios`

| column | type | notes |
|---|---|---|
| `key` | `String(40)` PK | `normal`, `misaligned_fin`, `person_near_pad` |
| `label` | `String(80)` | menu label |
| `expected_verdict` | `Enum(Verdict)` | asserted by the Playwright spec (SH-010) |
| `source_ref` | `String(512)` | the bundled fixture — a real image (FR-036) |
| `manual_inputs_json` | `JSON` | complete, so a demo never pauses for input |
| `zone_points_json` | `JSON` nullable | set for `person_near_pad` |
| `sort_order` | `SmallInteger` | menu order |

Seeded on first start. Every demo scenario carries a complete `manual_inputs_json`, which is why
a demo never reaches the `paused` state and always reaches a verdict (SC-001, SC-008).

### Entity relationships

```text
runs 1───* findings          cascade delete
runs 1───1 danger_zones      one zone per run in the MVP
runs 1───* checklist_steps   exactly 5, positions 1–5, unique per run
runs 1───* manual_inputs     one row per field
runs 1───* run_events        monotonic seq, unique per run
runs 1───1 reports           unique per run
demo_scenarios               standalone reference data, no FK to runs
```

### Local media

Images are written under `apps/api/media/` as `{run_id}/{name}.{ext}` and referenced from
`source_ref` and `annotated_ref` **relative to that root**. The path never leaves the API
process. NFR-005 permits retention of a completed run's images so history and shared links work;
the spec's Assumptions record that there is no automated expiry and no user-facing delete in the
MVP.

---

## 4. Lifecycle

### Run status

```text
                    ┌──────────── resume via Command(resume=...) ────────────┐
                    ▼                                                        │
  created ──▶ running ──▶ paused ──▶ running ──▶ completed                  │
                 │                                                          │
                 └──▶ failed  (module catastrophe, or interrupted_by_restart)
```

`running → failed` happens only for a run that cannot be completed safely. `completed` and
`failed` are terminal. There is no path from `paused` to `completed` that skips
`Command(resume=...)`, and no path from `failed` back to `running` — a failed run stays visible
in history with its reason (R12).

### Checklist step status

`pending → running → passed | failed | blocked → running → …`

Step 4 (`weather_manual`) is the only step that can enter `blocked`, and only when a mandatory
input is absent. Because the graph restarts the whole node on resume (R2), the `weather_manual`
node calls `interrupt()` as its **first statement**; all validation lives in the returned
`pending_question` state, not in code that would re-run.

### Streaming order guarantee

For any run, the persisted `run_events` sequence is append-only and `seq` is assigned inside the
same transaction that appends the row. A client that has consumed up to `seq = N` has therefore
seen every event that preceded `N` in causal order, which is what SC-006's "no dropped verdict
state during a continuous 5-minute session" requires.

---

## 5. Derived values, restated for implementers

| Value | Derivation | Source |
|---|---|---|
| `severity` | detector classification, then `apply_confidence_floor()`, never downgraded | `rule_engine/config.py` |
| `verdict` | the three-rule order over findings + manual rules | `rule_engine/verdict.py` |
| `risk_score` | banded saturating formula; advisory, never an input to verdict | `rule_engine/risk.py` |
| `reasons` | warnings and criticals, ordered by severity then step position | `rule_engine/verdict.py` |
| `recommended_actions` | one rule-derived action per reason, always present without a model | `rule_engine/verdict.py` |
| `near_threshold_note` | `is_threshold_ambiguous()` over every `Measurement` | `rule_engine/types.py` |
| `checklist[].status` | `passed` when the step emitted no warning/critical, else `failed` | `agent/graph.py` |
| `narrative_text` | model output, or null → template path | `agent/narrative.py` |

The first six rows are all `rule_engine` outputs, and `rule_engine` imports nothing from `cv/` or
`agent/` (R6). That is the mechanism by which no model can reach a verdict (Constitution 2.I).
