# Contract: Server-Sent Event stream

**Feature**: `001-launchguard-mvp` | **Date**: 2026-09-29
**Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md) | **API**: [api.md](./api.md)

Constitution 3.IV requires agent progress to be streamed so each checklist step animates live as it
is evaluated. This document defines that stream: its wire format, its event grammar, and the
guarantees a client may rely on.

## Transport

`GET /api/runs/{run_id}/stream` → `text/event-stream; charset=utf-8`

The stream is driven by LangGraph's `stream_events(..., version="v3")`, whose `interrupts`,
`interrupted`, and `output` fields map onto the events below (R2). Every event is **first
persisted** to `run_events` with a monotonic per-run `seq`, and only then published to live
subscribers. Nothing is ever emitted that is not already in the log.

```text
id: 7
event: finding.raised
data: {"seq":7,"at":"2026-09-29T14:20:12.884Z","payload":{ … }}

:heartbeat

id: 8
event: checklist.step.started
data: {"seq":8,"at":"2026-09-29T14:20:12.910Z","payload":{ … }}
```

- `id:` is the per-run `seq`. It is the value the client echoes back as `Last-Event-ID`.
- `data:` is a single-line JSON envelope, so no event ever contains a raw newline.
- `:heartbeat` is an SSE comment carrying no `id`, sent every 15 seconds while a run is still
  non-terminal, to stop intermediaries closing an idle connection.

### Response headers

Set by the API and preserved by the Next.js proxy (R5):

```text
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no
```

`no-transform` prevents compression middleware from buffering the stream; `X-Accel-Buffering` does
the same for a future nginx hop. The proxy strips any upstream `Content-Length` so the transfer
stays chunked, and unsubscribes from the pub/sub on `req.signal` when the tab closes.

## Envelope

Every non-heartbeat event uses one envelope:

```json
{
  "seq": 7,
  "at": "2026-09-29T14:20:12.884Z",
  "payload": { }
}
```

`seq` is strictly increasing by exactly 1 within a run. A client that has consumed up to `seq = N`
has therefore seen every event that causally preceded `N`, which is what SC-006's "no dropped
verdict state during a continuous 5-minute session" requires.

## Event grammar

| Event | Emitted when | Payload |
|---|---|---|
| `run.started` | The run is created, before any detection | `run_id`, `mode`, `source_type`, `steps[]` |
| `checklist.step.started` | A step begins | `position`, `step_key`, `label` |
| `finding.raised` | A detection step emits a finding | the full `Finding` object |
| `checklist.step.finished` | A step ends | `position`, `step_key`, `status`, `finding_count` |
| `run.awaiting_input` | The graph interrupts at step 4 | `missing[]`, `fields[]` |
| `run.completed` | The verdict is fixed and persisted | `verdict`, `risk_score`, `reasons[]`, `report_id`, `narrative.status = "pending"` |
| `report.narrative_ready` | The model returned, timed out, or is absent | `narrative.status`, `narrative.text`, `narrative.model` |
| `run.failed` | The run cannot complete safely | `reason`, `message` |

### `run.started`

```json
{
  "seq": 1,
  "at": "2026-09-29T14:20:11.004Z",
  "payload": {
    "run_id": "0f9c1f2e-…",
    "mode": "inspection",
    "source_type": "image_upload",
    "steps": [
      { "position": 1, "step_key": "body", "label": "Inspect body" },
      { "position": 2, "step_key": "fins", "label": "Check fins" },
      { "position": 3, "step_key": "launchpad_area", "label": "Check launchpad area" },
      { "position": 4, "step_key": "weather_manual", "label": "Weather & manual inputs" },
      { "position": 5, "step_key": "decision", "label": "Generate decision" }
    ]
  }
}
```

The step list is sent in FR-021's fixed order, so the client can render the full timeline skeleton
before the first detection completes.

### `finding.raised`

The full `Finding` object, in the same shape as the `findings[]` entry in
[`POST /api/monitor/{run_id}/frame`](./api.md) and in the report. Emitted per finding, not per
step, so overlays can appear as they are detected rather than in a batch at the end of a step —
this is what makes the stream feel live rather than merely asynchronous.

```json
{
  "seq": 4,
  "at": "2026-09-29T14:20:12.410Z",
  "payload": {
    "module": "cv.fins",
    "check_id": "fin.alignment",
    "severity": "warning",
    "message": "Fin angle deviation appears to be 4.2°, which may exceed the 3.0° warning threshold.",
    "confidence": 0.81,
    "metrics": [
      { "name": "fin_angle_deviation", "value": 4.2, "unit": "deg", "error_margin": 1.5, "threshold": 3.0 }
    ],
    "overlay": {
      "kind": "arc",
      "check_id": "fin.alignment",
      "points": [],
      "radius": 0.08,
      "start_deg": 4,
      "end_deg": 96,
      "label": "4.2° deviation"
    },
    "step_position": 2,
    "degraded": false,
    "low_confidence_critical": false,
    "near_threshold_note": "Measured 4.2° ± 1.5°; the warning threshold is 3.0°, so this outcome is not distinguishable from the adjacent severity."
  }
}
```

Two details in this payload carry constitutional weight:

- `near_threshold_note` is populated exactly when `is_threshold_ambiguous()` is true — the
  measurement sits within its own error margin of a threshold. This is the FR-043 and SH-007
  disclosure, delivered to the UI as it happens rather than only in the printed report.
- `metrics[].threshold` records the threshold the value was compared against, so a reviewer can
  re-derive the severity from the payload alone without knowing the configuration.

### `run.awaiting_input`

```json
{
  "seq": 19,
  "at": "2026-09-29T14:20:13.402Z",
  "payload": {
    "missing": ["wind_speed_ms", "visibility", "precipitation", "area_cleared"],
    "fields": [
      { "name": "wind_speed_ms", "label": "Wind speed", "type": "number", "unit": "m/s", "min": 0, "max": 60, "required": true },
      { "name": "visibility", "label": "Visibility", "type": "enum", "options": ["good", "moderate", "poor"], "required": true },
      { "name": "precipitation", "label": "Precipitation", "type": "enum", "options": ["none", "light", "heavy"], "required": true },
      { "name": "area_cleared", "label": "Pad area cleared", "type": "boolean", "required": true },
      { "name": "notes", "label": "Notes", "type": "text", "max_length": 500, "required": false }
    ]
  }
}
```

`fields` is the server's registry, so the client builds its Zod schema from this document rather
than from a duplicated list (Constitution 4.V, FR-023). No run-control action is possible from
this event alone; the client pairs it with a `POST /api/runs/{run_id}/manual-inputs`.

After this event the stream stays **open** and idle — the graph is suspended, not finished — and
resumes with the next event once inputs are submitted. Heartbeats continue meanwhile.

### `run.completed`

```json
{
  "seq": 27,
  "payload": {
    "verdict": "HOLD",
    "risk_score": 52,
    "report_id": "8a1b…",
    "narrative": { "status": "pending" },
    "reasons": [
      { "check_id": "fin.alignment", "severity": "warning", "message": "…", "confidence": 0.81, "ambiguous": true }
    ]
  }
}
```

This event is emitted **as soon as the verdict is fixed**, before the narrative call is made. The
verdict therefore reaches the UI within NFR-001's 5-second budget regardless of model latency,
and `run.completed` is the only event whose `verdict` field the client is allowed to render
(FR-025, Constitution 2.I).

`narrative.status` is `"pending"` here in every case. It is never `"available"` in this event, so
the verdict can never appear to depend on the model having answered.

### `report.narrative_ready`

```json
{
  "seq": 31,
  "payload": {
    "narrative": { "status": "available", "text": "…", "model": "gpt-4o-mini" }
  }
}
```

On timeout, error, or absent `OPENAI_API_KEY`:

```json
{
  "seq": 28,
  "payload": {
    "narrative": { "status": "unavailable", "text": null, "model": null }
  }
}
```

`unavailable` is a first-class, explicitly-rendered state. The client shows the template report
with a "Narrative unavailable — verdict unaffected" note, and does not treat the absence as an
error (FR-026, SH-008).

### `run.failed`

```json
{
  "seq": 4,
  "payload": {
    "reason": "interrupted_by_restart",
    "message": "This run was interrupted when the service restarted and was not completed. No verdict was produced."
  }
}
```

Reasons: `interrupted_by_restart` (R12), `unreadable_source`, `internal_error`. A failed run never
carries a verdict, and the client renders it as a terminal state with its reason rather than
retrying silently — the conservative choice required by NFR-003 and SH-002.

## Terminal and reconnect semantics

| Situation | Behaviour |
|---|---|
| Run reaches `completed` | `run.completed` then `report.narrative_ready`, then the server closes the stream cleanly. |
| Run reaches `failed` | `run.failed`, then close. |
| Client disconnects mid-run | Nothing changes. The run continues; events keep accumulating in `run_events`. |
| Client reconnects with `Last-Event-ID: 19` | Server replays every event with `seq > 19` from the database, then attaches live. No gap, no duplicate. |
| Client reconnects with no `Last-Event-ID` | Server replays the whole log, then attaches live. |
| Client reconnects to a finished run | Full replay, then a clean close. A late tab sees the complete decision. |
| No events for 15 s while running | `:heartbeat` comment. No `seq` consumed. |
| Two tabs on one run | Both receive every event from `seq = 1`; neither writes to the run. Satisfies the spec's concurrency edge case. |

Because persistence precedes publication, the in-process pub/sub is an optimisation for latency,
not the source of truth. Replacing it with a broker for a multi-worker deployment would not change
this contract — which is why the single-worker limitation documented in
[quickstart.md](../quickstart.md) is a deployment constraint rather than an API one (R5).

## Client obligations

1. Render the verdict badge only from `run.completed` or `GET /api/runs/{run_id}/report`, never
   from an optimistic local guess.
2. Show the disclaimer wherever a verdict, risk score, or finding list is visible, on all five
   screens (FR-037).
3. Convey severity with text and an icon as well as colour (FR-041, Constitution 4.VI).
4. Treat `degraded: true` findings as a visible condition, not a silent one — a `warning` at
   `confidence 0.0` means the check could not run (Constitution 2.II).
5. Pass `narrative.status` through to the UI rather than substituting a fallback string, so
   `unavailable` is visibly distinct from `pending` and from `available`.
