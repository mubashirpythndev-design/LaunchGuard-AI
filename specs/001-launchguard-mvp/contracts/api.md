# Contract: HTTP API surface

**Feature**: `001-launchguard-mvp` | **Date**: 2026-09-29
**Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)
**Events**: [events.md](./events.md)

## Generation contract

`packages/contract/openapi.json` is **not authored in this repository**. It is produced by
`scripts/export_openapi.py`, which imports the FastAPI app from `apps/api/app/main.py` and writes
`app.openapi()` to disk. No server is started, so the export cannot be affected by request-time
state.

`@hey-api/openapi-ts` then generates, from that single file:

- TypeScript interfaces — for request and response bodies
- Zod v4 schemas — one per reusable definition, per request layer, and per response layer
- A typed fetch SDK

`packages/contract/src/` is generated, git-ignored, and never hand-edited. `apps/web` declares no
API type of its own; `apps/web/lib/schemas.ts` contains re-exports only. CI runs the generation
and then `git diff --exit-code`, so a stale contract fails the build rather than drifting
silently (Constitution 3.I, R1).

This document is the **human-readable intent** behind that generated document. Where it and the
generated `openapi.json` disagree, the generated document is correct and this file is a bug.

## Conventions

- All paths are prefixed `/api`. The browser talks only to the Next.js origin; the proxy at
  `apps/web/app/api/[...path]/route.ts` forwards to the API.
- All request and response bodies are `application/json`, except image uploads
  (`multipart/form-data`) and live frames (raw `image/jpeg`).
- All timestamps are RFC 3339 with an explicit UTC offset.
- `Confidence` is a number in `[0.0, 1.0]`. `RiskScore` is an integer in `[0, 100]`.
- Ids are UUIDv4 strings. Share tokens are 43-character `token_urlsafe(32)` values.

### Error envelope

Every non-2xx response uses one shape, so the client has a single error path:

```json
{
  "error": {
    "code": "UNSUPPORTED_MEDIA_TYPE",
    "message": "Only JPG, PNG, and WebP images are accepted. Received: application/pdf.",
    "field": null
  }
}
```

`field` names the offending form field or query parameter when the failure is attributable to
one, which is what makes FR-023's inline validation possible.

| Status | `code` | Used by |
|---|---|---|
| 400 | `INVALID_ZONE` | fewer than 3 points, self-intersecting, or degenerate polygon |
| 400 | `INVALID_MANUAL_INPUT` | out-of-range manual value, with `field` set (FR-023) |
| 404 | `RUN_NOT_FOUND` | unknown run id |
| 404 | `SCENARIO_NOT_FOUND` | unknown demo scenario key |
| 409 | `ZONE_NOT_SET` | frame submitted before a zone exists |
| 410 | `SHARE_NOT_AVAILABLE` | share token valid but its run was deleted (spec edge case) |
| 413 | `FILE_TOO_LARGE` | upload over 10 MB (FR-008) |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | non-image upload (FR-008) |
| 422 | `CORRUPT_IMAGE` | zero-byte or undecodable image (FR-008) |
| 503 | `MODEL_UNAVAILABLE` | narrative requested but `OPENAI_API_KEY` absent — **never** returned for inspection, monitor, or report reads (NFR-006) |

`MODEL_UNAVAILABLE` is listed only for completeness. A report is always readable: the narrative
degrades to the template path and the response carries `narrative.status = "unavailable"` with a
200 (FR-026).

---

## Endpoints

### Health and configuration

#### `GET /api/health`

Used by the demo script to gate startup, and by the dashboard to show whether the narrative model
is configured.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "model_configured": true,
  "workers": 1
}
```

#### `GET /api/config`

Publishes every configurable threshold so the UI can render current settings and the pinned
confidence floor rather than hard-coding them. This is the API half of Constitution 2.II's
requirement that the low-confidence threshold be pinned in the API config (R8).

```json
{
  "min_confidence_for_ok": 0.35,
  "thresholds": {
    "fin_angle_warning_deg": 3.0,
    "fin_angle_critical_deg": 6.0,
    "fin_angle_error_margin_deg": 1.5,
    "wind_warning_ms": 10.0,
    "wind_critical_ms": 15.0,
    "poor_visibility_severity": "warning",
    "heavy_precipitation_severity": "warning",
    "area_not_cleared_severity": "critical",
    "object_in_zone_severity": "critical",
    "motion_sensitivity": 0.5,
    "detector_conf": 0.25,
    "detector_iou": 0.45,
    "zone_occupancy": true
  },
  "disclaimer": "Decision-support tool. Not a replacement for certified range safety."
}
```

The `disclaimer` is served from the API rather than duplicated in the frontend, so the web app and
the persisted report render the identical mandated string (FR-037, SH-004).

### Pre-Launch Inspection

#### `POST /api/inspections`

`multipart/form-data` with a single `file` part. JPG, PNG, or WebP, at most 10 MB (FR-007).

The preview the engineer sees immediately is a local object URL created before the request is
sent, so it renders with no server round-trip. This endpoint returns only the run handle.

**201 Created**

```json
{
  "run_id": "0f9c1f2e-6c2a-4a1e-9a0b-6b6b1c2d3e4f",
  "mode": "inspection",
  "status": "running",
  "stream_url": "/api/runs/0f9c1f2e-6c2a-4a1e-9a0b-6b6b1c2d3e4f/stream",
  "expected_steps": ["body", "fins", "launchpad_area", "weather_manual", "decision"]
}
```

**Rejections** — each returns a specific message and **no run is created** (FR-008):
`413 FILE_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE`, `422 CORRUPT_IMAGE`.

### Launchpad Monitor

#### `POST /api/monitor`

Creates a monitor run. `source_type` is `image_upload`, `video_upload`, or `live_stream`. For the
two upload forms the same file rules as inspection apply.

**201 Created** — same shape as inspection, with `mode: "monitor"`.

#### `POST /api/monitor/{run_id}/frame`

Raw `image/jpeg` request body. One frame in flight at a time, enforced client-side by skipping a
capture while a request is outstanding (R4). Returns this frame's findings and the live zone
status.

**200 OK**

```json
{
  "seq": 412,
  "zone_status": "DANGER",
  "processing_ms": 214,
  "frame_width": 1280,
  "frame_height": 720,
  "findings": [
    {
      "module": "cv.zone",
      "check_id": "zone.occupancy",
      "severity": "critical",
      "message": "A person appears to be inside the marked danger zone.",
      "confidence": 0.88,
      "metrics": [
        { "name": "overlap_ratio", "value": 0.41, "unit": "ratio", "error_margin": null, "threshold": 0.0 }
      ],
      "overlay": {
        "kind": "bbox",
        "check_id": "zone.occupancy",
        "points": [[0.62, 0.44], [0.79, 0.71]],
        "radius": null, "start_deg": null, "end_deg": null,
        "label": "person"
      },
      "step_position": 3,
      "degraded": false,
      "low_confidence_critical": false,
      "near_threshold_note": null
    }
  ]
}
```

`zone_status` is `CLEAR`, `WARNING`, or `DANGER` (FR-016). `processing_ms` is returned so
NFR-002's 500 ms budget is observable in the UI during the demo rather than only in CI.

`409 ZONE_NOT_SET` when a frame arrives before a zone is saved, since containment cannot be
evaluated without one.

#### `PUT /api/monitor/{run_id}/zone`

```json
{
  "points": [[0.18, 0.22], [0.74, 0.19], [0.81, 0.66], [0.24, 0.71]],
  "label": "Pad danger zone"
}
```

Points are normalized 0–1 and stored alongside the source frame dimensions, so the same polygon
re-renders in the same place at any display size (FR-012, FR-013).

**200 OK** returns the saved zone with its `source_width` / `source_height`.

`400 INVALID_ZONE` names the specific problem for a polygon with fewer than three points, a
self-intersecting outline, or zero area.

#### `DELETE /api/monitor/{run_id}/zone`

Removes the zone. Subsequent frames return findings with no `zone.occupancy` check.

#### `GET /api/monitor/{run_id}/log`

```json
{
  "entries": [
    {
      "at": "2026-09-29T14:22:05.101Z",
      "zone_status": "CLEAR",
      "check_ids": [],
      "max_severity": "ok"
    },
    {
      "at": "2026-09-29T14:22:05.317Z",
      "zone_status": "DANGER",
      "check_ids": ["zone.occupancy"],
      "max_severity": "critical"
    }
  ]
}
```

Chronological, oldest first (FR-017).

### Manual inputs and the agent pause

#### `GET /api/runs/{run_id}/required-inputs`

Lets the client render the manual-input form from the server's registry rather than a duplicated
list of field definitions.

```json
{
  "run_id": "0f9c1f2e-…",
  "missing": ["wind_speed_ms", "visibility", "precipitation", "area_cleared"],
  "fields": [
    { "name": "wind_speed_ms",   "label": "Wind speed",     "type": "number", "unit": "m/s", "min": 0, "max": 60, "required": true },
    { "name": "visibility",      "label": "Visibility",     "type": "enum",   "options": ["good", "moderate", "poor"], "required": true },
    { "name": "precipitation",   "label": "Precipitation",  "type": "enum",   "options": ["none", "light", "heavy"], "required": true },
    { "name": "area_cleared",    "label": "Pad area cleared", "type": "boolean", "required": true },
    { "name": "notes",           "label": "Notes",          "type": "text",   "max_length": 500, "required": false }
  ]
}
```

The client builds a Zod schema from this. That is what lets one generated contract drive both
TypeScript types and runtime form validation (Constitution 4.V, FR-023).

#### `POST /api/runs/{run_id}/manual-inputs`

```json
{
  "wind_speed_ms": 8.2,
  "visibility": "good",
  "precipitation": "none",
  "area_cleared": true,
  "notes": "Optional context"
}
```

Validates, persists, then resumes the graph with `Command(resume=...)` on the same `thread_id`
(R2). A partial submission is accepted — the run stays `paused` and `missing` shrinks — which is
what the interrupt retry loop provides without a second round-trip. The response is the updated
required-inputs document plus the current `status`.

`400 INVALID_MANUAL_INPUT` with `field` set for an out-of-range value, e.g. a negative wind
speed; the form rejects it inline and does not submit (FR-023).

### Runs, streaming, and reports

#### `GET /api/runs/{run_id}/stream`

`text/event-stream`. Full event grammar in [events.md](./events.md). Supports `Last-Event-ID`
replay, `:heartbeat` every 15 s, and closes cleanly when the run reaches a terminal state.

#### `GET /api/runs/{run_id}/events?after={seq}`

The same event stream as JSON. Used by the demo script and by tests, which cannot hold an
`EventSource` open. `after` defaults to `0`.

#### `GET /api/runs/{run_id}`

```json
{
  "run_id": "0f9c1f2e-…",
  "mode": "inspection",
  "source_type": "image_upload",
  "status": "completed",
  "status_reason": null,
  "verdict": "HOLD",
  "risk_score": 52,
  "created_at": "2026-09-29T14:20:11.004Z",
  "completed_at": "2026-09-29T14:20:14.221Z",
  "thresholds": { "fin_angle_warning_deg": 3.0, "…": "…" },
  "source": { "width": 1280, "height": 960, "url": "/api/runs/0f9c1f2e-…/image" }
}
```

A `paused` run returns `200` with `status: "paused"` and a null verdict — never an error, and
never a defaulted `GO` (spec edge case).

#### `GET /api/runs?verdict={verdict}&limit={n}&offset={n}`

```json
{
  "total": 5,
  "items": [ { "run_id": "…", "verdict": "NO-GO", "risk_score": 88, "status": "completed", "created_at": "…", "max_severity": "critical" } ]
}
```

`verdict` is optional. Omit it for all verdicts; the History screen filters by it (FR-032).

#### `GET /api/runs/latest`

Dashboard summary: latest verdict, risk score, checklist status, and the most recent runs in one
round-trip (FR-031).

#### `GET /api/runs/{run_id}/report`

```json
{
  "report_id": "8a1b…",
  "run_id": "0f9c1f2e-…",
  "verdict": "HOLD",
  "risk_score": 52,
  "verdict_attribution": "Verdict computed by rules; explanation by AI",
  "disclaimer": "Decision-support tool. Not a replacement for certified range safety.",
  "checklist": [
    { "position": 1, "step_key": "body",       "label": "Inspect body",          "status": "passed",  "finding_count": 5 },
    { "position": 2, "step_key": "fins",       "label": "Check fins",            "status": "failed",  "finding_count": 1 },
    { "position": 3, "step_key": "launchpad_area", "label": "Check launchpad area", "status": "passed", "finding_count": 1 },
    { "position": 4, "step_key": "weather_manual", "label": "Weather & manual inputs", "status": "passed", "finding_count": 4 },
    { "position": 5, "step_key": "decision",   "label": "Generate decision",     "status": "passed",  "finding_count": 0 }
  ],
  "reasons": [
    { "check_id": "fin.alignment", "severity": "warning", "message": "Fin angle deviation appears to be 4.2°, which may exceed the 3.0° warning threshold.", "confidence": 0.81, "ambiguous": true }
  ],
  "recommended_actions": [
    { "check_id": "fin.alignment", "action": "Re-measure the fin alignment with the camera square-on to the vehicle, then re-run the inspection." }
  ],
  "findings": [ { "…": "full Finding objects" } ],
  "narrative": { "status": "available", "text": "…", "model": "gpt-4o-mini" },
  "annotated_image_url": "/api/runs/0f9c1f2e-…/annotated.png",
  "generated_at": "2026-09-29T14:20:14.900Z",
  "share_token": null
}
```

Notes on fields that carry constitutional weight:

- `verdict_attribution` is the fixed string required by FR-025.
- `narrative.status` is `unavailable` with `text: null` when the model failed or is absent. The
  response is still `200` and still contains the verdict, risk score, checklist, and reasons
  (FR-026, SH-008).
- `reasons[].ambiguous` is `true` when a measurement sits within its error margin of a threshold,
  and `reasons[].message` then carries the not-distinguishable note (FR-043, SH-007).
- `recommended_actions` is always populated from rule-derived defaults before the model runs, so
  a narrative timeout cannot empty it.

#### `GET /api/runs/{run_id}/image` and `GET /api/runs/{run_id}/annotated.png`

Local-only image bytes. Served for history and the report viewer. Never proxied to a third party
(FR-039, NFR-005).

### Sharing

#### `POST /api/runs/{run_id}/share`

Creates or returns the run's share token. Idempotent — re-sharing returns the existing token so a
link does not rot on a second click.

```json
{ "token": "kZ3…", "url": "/share/kZ3…", "read_only": true, "created_at": "2026-09-29T14:25:00Z" }
```

The token is an unguessable 256-bit capability, which is the MVP's answer to
spec Assumption 8 — authentication and multi-tenancy are out of scope (FR-040), so the token
grants access to exactly one report and no controls (FR-033).

#### `GET /api/share/{token}`

A reduced report document: verdict, risk score, disclaimer, checklist, reasons, recommended
actions, narrative, and annotated image. **No** run controls, no zone, no manual-input form, no
detection log, and no listing of other runs. Selecting a token that no longer resolves to a run
returns `410 SHARE_NOT_AVAILABLE`, which the client renders as an explicit not-available state
rather than a blank report or an error page (spec edge case).

### Demo mode

#### `GET /api/demo/scenarios`

```json
{
  "scenarios": [
    { "key": "normal",          "label": "Normal — all clear",          "expected_verdict": "GO" },
    { "key": "misaligned_fin",  "label": "Misaligned fin",              "expected_verdict": "HOLD" },
    { "key": "person_near_pad", "label": "Person near pad",             "expected_verdict": "NO-GO" }
  ]
}
```

Exactly three, matching Constitution 6.I. The endpoint exposes **no** expected findings, no risk
score, and no verdict other than `expected_verdict`, which is metadata the user is told in
advance — not a leak of a stored result. There is nothing else to leak, because no result is
stored: a demo run executes the identical pipeline (FR-036).

#### `POST /api/demo/scenarios/{key}/run`

**201 Created** with the usual run handle. Bundled manual inputs are complete, so a demo run never
pauses. With the network disabled the narrative call fails and the run completes on the template
path with the expected verdict (FR-035, SC-008).

---

## Cross-cutting guarantees

| Guarantee | Mechanism |
|---|---|
| No third-party image data (FR-039, SH-009) | The narrative payload is built from an explicit field allow-list in `agent/narrative.py`; a unit test asserts the serialized payload contains no `data:image`, `base64`, image MIME type, or absolute path. All overlay geometry is normalized 0–1, so pixel coordinates cannot leak by existing. |
| Verdict never comes from the model (FR-001, Constitution 2.I) | The model is called after the `runs.verdict` and `reports` rows are committed, and its output schema is `{narrative, recommended_actions[]}` — there is no verdict field to write. |
| Verdict survives model failure (SH-006) | `reports` rows are written with `narrative_status = 'pending'` before the call; the narrative update touches narrative columns only. |
| Two tabs stay consistent (spec concurrency edge case) | Both subscribe to the same persisted `run_events` log with independent `Last-Event-ID` positions (R5). |
| Abandoned paused run stays retrievable (spec edge case) | LangGraph's `AsyncSqliteSaver` persists the interrupt, so `paused` survives an API restart (R2, R12). |
| Manual input rules never come from CV | `rule_engine/manual.py` evaluates the four mandatory fields. `rule_engine` imports nothing from `cv/` or `agent/` (R6). |
