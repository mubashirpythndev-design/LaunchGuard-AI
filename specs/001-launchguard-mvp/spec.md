# Feature Specification: LaunchGuard AI MVP

**Feature Branch**: `001-launchguard-mvp`
**Created**: 2026-09-29
**Status**: Draft
**Input**: User description: "LaunchGuard AI — an AI co-pilot for low-cost rocket safety inspection. A camera-based web app that inspects rocket hardware and the launchpad from images / video / webcam, reasons through a launch checklist like a safety officer, and outputs GO / HOLD / NO-GO with reasons and actions. 6 user stories (Pre-Launch Inspection, Launchpad Monitor, Smoke/Fire/Leak, Agentic Safety Report, Mission Dashboard & History, Demo mode), 3 manual/context inputs, NFRs, UX requirements, 5 screens, explicit out-of-scope list, and hackathon success metrics." Full prompt text preserved verbatim in `history/prompts/001-launchguard-mvp/`.

**Note on scope of this document**: This specification states WHAT is needed and WHY. It deliberately
names no framework, model, library, or vendor. Technology decisions belong in `plan.md`.

---

## Problem

Rocket development has costly, visually detectable failure points: cracks, dents, burn marks,
misaligned fins, missing bolts, fuel or liquid leaks, smoke and fire, and foreign objects or
people in the danger zone. Industrial inspection systems are expensive. Teams in emerging
aerospace ecosystems need an affordable alternative that a small launch team can actually run
from a laptop on the pad.

## Vision

An AI co-pilot for low-cost rocket safety inspection. A camera-based web app that inspects rocket
hardware and the launchpad, reasons through a launch checklist like a safety officer, and outputs
a verdict of **GO**, **HOLD**, or **NO-GO** with the reasons and the actions behind it.

## Users

| Persona | Need |
|---|---|
| Launch Engineer (primary) | Fast pre-launch visual inspection with a clear verdict and next actions |
| Range Safety Officer | Live pad monitoring; instant alert when someone or something enters the danger zone |
| Team Lead / Judge | Understand status at a glance; export or share the report |

---

## Verdicts, Severity, and Risk Score

- **Finding severity** takes exactly one of three values: `ok`, `warning`, `critical`.
- **Verdict** takes exactly one of three values: `GO`, `HOLD`, `NO-GO`.
- **Verdict rules are deterministic** and evaluated in this order:
  1. Any finding at `critical`, or any manual input rule firing at `critical` → **NO-GO**
  2. Otherwise, any finding at `warning`, any manual input rule firing at `warning`, or any
     mandatory manual input missing → **HOLD**
  3. Otherwise → **GO**
- **Risk score** is an integer 0–100 derived from finding severities weighted by finding
  confidence. The exact formula is a planning decision (recorded in `plan.md`), not a
  specification one. The risk score is **advisory**: it is shown alongside the verdict and
  MUST NOT alter it.
- Threshold values (fin angle, wind speed, visibility, precipitation, zone occupancy) are
  **configurable** rather than hard-coded, with the defaults listed in this specification.

---

## User Scenarios & Testing *(mandatory)*

> Per Constitution 2.IV, acceptance scenarios that describe what the system "sees" are written in
> hedged language. Any story that surfaces a verdict carries the disclaimer as an explicit
> acceptance condition.

### User Story 1 - Pre-Launch Inspection (Priority: P1, source US-1)

As a launch engineer, I upload a photograph of my rocket and get body and fin inspection results,
so that I can catch a visible defect before the vehicle is moved to the pad.

**Why this priority**: This is the core value of the product and the cheapest to demonstrate
end to end. Everything else either extends it (monitoring), orchestrates it (the agent), or
packages it (dashboard, history, demo). If only one story ships, it should be this one.

**Independent Test**: Upload one fixture image of an intact rocket and one of a cracked rocket.
Each produces a complete, per-module result set with severities, confidence, and annotations,
with no network access to any language model. Delivers a usable inspection verdict on its own.

**Acceptance Scenarios**:

1. **Given** an engineer on the Pre-Launch Inspection screen, **When** they drag a JPG, PNG, or
   WebP file of at most 10 MB onto the drop area or pick one via the file picker, **Then** a
   preview of the uploaded image appears immediately, before inspection completes.
2. **Given** an uploaded image, **When** inspection completes, **Then** findings are reported for
   each of: cracks or scratches, dents, surface or paint damage, dark or burn marks, fin symmetry
   reported as an angle deviation in degrees, and missing bolts or parts.
3. **Given** a completed inspection, **When** the engineer views the result, **Then** the image
   is shown with annotation overlays (boxes, lines, angle arcs) that can be toggled on and off
   per module.
4. **Given** any finding, **When** the engineer expands it, **Then** it shows severity,
   confidence, a human-readable message, and the measured metrics behind it.
5. **Given** a measured fin angle deviation, **When** the deviation exceeds 3°, **Then** the fin
   finding is `warning`; **When** it exceeds 6°, **Then** it is `critical`; and the engineer can
   change both thresholds in configuration.
6. **Given** a result page displaying findings, **When** the page renders, **Then** the
   disclaimer "Decision-support tool. Not a replacement for certified range safety." is visible,
   and finding messages use hedged wording such as "appears" or "possible" rather than asserting
   certainty.

---

### User Story 2 - Launchpad Monitor (Priority: P2, source US-2)

As a range safety officer, I define a danger zone and monitor an image, a video, or my live
webcam, so that I am alerted immediately when a person or an object enters the danger zone.

**Why this priority**: This is the second-highest-value mode and the one that demonstrates the
live/streaming capability. It depends on the same finding pipeline as Story 1, so it adds the
zone editor and a real-time loop without new core concepts.

**Independent Test**: With a fixture frame containing one person inside a drawn polygon and one
person outside it, the monitor reports `critical` for the inside person, `ok` for the outside
person, and saves the zone with the run. No language model required.

**Acceptance Scenarios**:

1. **Given** a frame displayed in the zone editor, **When** the officer draws a polygon danger
   zone and saves, **Then** the zone is stored with the run using normalized 0–1 coordinates so
   it survives a change of display size, and **When** they reopen that run, **Then** the same
   polygon is shown in the same place.
2. **Given** a saved danger zone, **When** a person is detected inside it, **Then** a `critical`
   finding is emitted; **When** a non-person object such as a tool is detected inside it, **Then**
   a `critical` finding is emitted by default and can be configured down to `warning`; **When** a
   person is detected outside it, **Then** no zone finding is emitted for that person.
3. **Given** a live webcam stream on a 1280px laptop, **When** monitoring is running, **Then** at
   least 2 frames per second are analyzed with visible end-to-end latency under 1.5 seconds.
4. **Given** monitoring is running, **When** the zone status changes, **Then** a prominent live
   status banner switches between `CLEAR`, `WARNING`, and `DANGER`, conveying each state with
   text and an icon as well as color, and an optional audible alert can be enabled and muted by
   the user.
5. **Given** a live or recorded source, **When** smoke, fire, leak, or abnormal motion cues are
   present, **Then** they are surfaced as findings per Story 3.
6. **Given** the live status banner, **When** it renders, **Then** the disclaimer is visible and
   the state is still fully legible with reduced-motion enabled and with color perception
   differences simulated.

---

### User Story 3 - Smoke, Fire, Leak, and Abnormal Motion (Priority: P6, source US-3)

As a launch engineer, I want smoke, flame, liquid pooling, and unexpected movement near the
vehicle base flagged, so that a developing incident is surfaced even before a full inspection
concludes.

**Why this priority**: These cues are what make the tool genuinely safety-relevant, but they are
decomposed from Story 2 (its acceptance criterion 5) and are the least mature detection
approach. They are last so that a time-boxed MVP still ships the three primary modes intact.
Because Story 2 depends on this capability existing, Story 2 may ship with these cues stubbed
and Story 3 completed afterwards.

**Independent Test**: Run the cue detectors against a fixture set containing a flame region, a
smoke region, a liquid pool, and a static frame with no cues, and confirm each produces a
finding of the same shape as a body or fin finding.

**Acceptance Scenarios**:

1. **Given** a frame containing a flame-like or smoke-like region, **When** the cue detectors
   run, **Then** the region appears to be flagged, and **Given** a frame whose base region
   changes between consecutive frames, **Then** that change appears to be abnormal motion and is
   flagged.
2. **Given** a visible liquid pooling or leak near the vehicle base, **When** the detectors run,
   **Then** a `warning` finding is emitted, escalating to `critical` when a fire cue is also
   present in the same run.
3. **Given** any cue finding, **When** it is rendered, **Then** it has exactly the same fields
   and rendering as a body, fin, or zone finding.

---

### User Story 4 - Agentic Safety Report (Priority: P3, source US-4)

As a launch engineer, I run the safety officer agent and watch it work through the checklist, so
that I understand not just the verdict but the ordered reasoning that produced it.

**Why this priority**: This is the product's differentiator and the demo's centerpiece, but it
orchestrates the other stories rather than adding detection capability, so it comes after
inspection and monitoring exist.

**Independent Test**: Start an agentic run on a fixture image with the mandatory manual inputs
deliberately omitted. The agent reaches the manual-inputs step, pauses, requests the missing
inputs in an in-app form, accepts them, resumes, and produces a complete report whose verdict
matches the rule engine's independent output.

**Acceptance Scenarios**:

1. **Given** a started run, **When** the agent executes, **Then** checklist steps run in this
   order and stream progress live to the user: (1) inspect body, (2) check fins, (3) check
   launchpad area, (4) check weather and manual inputs, (5) generate decision.
2. **Given** the run has reached step 4 with wind speed, visibility, precipitation, or
   area-cleared confirmation missing, **When** the agent evaluates, **Then** it pauses and asks
   for exactly the missing inputs through an in-app form, and resumes automatically once they
   are submitted.
3. **Given** a completed run, **When** the report is generated, **Then** it contains the verdict,
   the risk score, a pass/fail line for every checklist step, the reasons in priority order, the
   recommended actions, the annotated images, a timestamp, and the run id.
4. **Given** a report containing narrative text and recommendations, **When** the engineer reads
   it, **Then** the verdict shown equals the rule engine's output exactly, the report states
   "Verdict computed by rules; explanation by AI", and no narrative text asks for or implies a
   change of verdict.
5. **Given** the language model is unavailable or times out, **When** the report is generated,
   **Then** a template-based report is still produced, containing the same verdict, risk score,
   checklist, and reasons, with the narrative section marked as unavailable.
6. **Given** any report, **When** it renders, **Then** the disclaimer is visible and the verdict
   is conveyed by text, icon, and color together.

---

### User Story 5 - Mission Dashboard and History (Priority: P5, source US-5)

As a team lead or judge, I want to see the latest verdict at a glance and browse past runs, so
that I can understand team status without reading every inspection.

**Why this priority**: Purely a presentation and retrieval layer over completed runs. It adds no
safety logic and is not needed to demonstrate a verdict, so it follows the core inspection,
monitoring, and reporting stories.

**Independent Test**: With five stored runs of varying verdicts, the dashboard shows the latest
verdict, risk score, and checklist status, and the history list can be filtered to a single
verdict and opened to the full report.

**Acceptance Scenarios**:

1. **Given** at least one completed run, **When** the engineer opens the dashboard, **Then** the
   latest verdict, a risk score gauge, the checklist status, and the recent runs are shown.
2. **Given** multiple stored runs, **When** the engineer views history, **Then** runs are listed
   and can be filtered by verdict, and opening one shows that run's full report.
3. **Given** an open report, **When** the engineer exports it, **Then** a print or PDF view is
   produced that is legible in both color and black-and-white, and a read-only shareable link can
   be generated that exposes the report without exposing controls or other runs.

---

### User Story 6 - Demo Mode (Priority: P4, source US-6)

As a team lead or judge, I click one button and see a complete, correct verdict, so that the
product can be evaluated reliably in a hackathon demo with no setup and no network.

**Why this priority**: It has no product value of its own, but it is the single highest-leverage
item for a time-boxed demo: it converts the three P0 stories into a repeatable one-click
demonstration. It ranks above the dashboard because a demo that cannot be trusted fails the
hackathon outright.

**Independent Test**: On a machine with the network disabled, trigger each of the three bundled
scenarios in turn and confirm the expected verdict, annotated image, reasons, and report.

**Acceptance Scenarios**:

1. **Given** the "Load demo scenario" menu, **When** the user picks Normal, Misaligned fin, or
   Person near pad, **Then** the corresponding bundled scenario runs to completion and yields
   `GO`, `HOLD`, and `NO-GO` respectively.
2. **Given** a bundled scenario, **When** it runs with the network disabled, **Then** it still
   completes and still yields its expected verdict, using the template-based report path.
3. **Given** a bundled scenario, **When** it completes, **Then** the annotated image, the ordered
   reasons, and the recommended actions are shown exactly as they would be for a real run, so
   that the demo is representative rather than mocked.

---

### Edge Cases

**Decision-critical boundaries**

- Fin angle deviation of exactly 3° or exactly 6° — the boundary must fall on the
  less-severe side, so that a measurement at the limit does not escalate.
- A measured fin deviation that is genuinely 3.0° but measured with up to 1.5° of error may read
  as 1.5° or 4.5°; a defect near the warning threshold may be reported as `ok`. This margin is
  accepted for the MVP and MUST be stated in the report whenever a fin measurement falls within
  the measurement error of a threshold.
- Wind speed of exactly 10 m/s and exactly 15 m/s — boundary falls on the less-severe side.
- A person whose bounding box overlaps the danger zone boundary — the rule is containment, so
  any overlap with the polygon counts as inside; this must be documented in the report.
- A person detected with low confidence — the zone rule still applies, because an unverified
  person in a danger zone is a hold-or-worse condition, never an `ok`.

**Module and input failures**

- A CV module that errors, times out, or returns very low confidence — the run continues and the
  module contributes a `warning` finding, never `ok` and never a crash.
- All CV modules failing in a single run — the verdict is `HOLD` with a prominent note that the
  inspection could not be completed, never `GO`.
- A mandatory manual input missing at report time — verdict is `HOLD`, with the missing input
  named in the reasons.
- Manual input entered with an out-of-range value, such as a negative wind speed — the form
  rejects it inline and does not submit.

**Input and source edge cases**

- Upload of a file that is not an image, exceeds 10 MB, or is a corrupt/zero-byte file — the
  upload is rejected with a specific message and the run does not start.
- A webcam stream that ends, is denied permission, or drops — the monitor shows a disconnected
  state, keeps the last known status clearly marked as stale, and offers a reconnect action.
- A video file with no detectable video track, or shorter than one frame.
- A frame that is entirely uniform, too dark, or too bright for detection — modules return low
  confidence and the run degrades to `HOLD` with a "conditions prevent reliable inspection" note.
- A polygon that is self-intersecting, has fewer than three points, or is degenerate — rejected
  with a message naming the problem.

**Concurrency and lifecycle**

- Two browser tabs streaming the same run — both stay consistent and neither corrupts the run.
- A run left mid-pause awaiting manual input, then abandoned — the run remains retrievable in
  history in a paused state rather than disappearing or silently defaulting to `GO`.
- A shareable link opened after the underlying run is deleted — the link shows a clear
  not-available state rather than an error or a blank report.

---

## Requirements *(mandatory)*

### Functional Requirements

**Verdict and severity**

- **FR-001**: The system MUST compute every verdict exclusively from structured findings and
  manual-input rule results, using the deterministic order defined in this specification. The
  language model MUST NOT participate in producing the verdict.
- **FR-002**: The system MUST allow only the severities `ok`, `warning`, `critical` and only the
  verdicts `GO`, `HOLD`, `NO-GO`.
- **FR-003**: The system MUST compute a risk score as an integer from 0 to 100 derived from
  finding severities weighted by finding confidence, and MUST display it as advisory information
  that does not affect the verdict.
- **FR-004**: The system MUST allow all detection thresholds (fin angle warning and critical,
  wind warning and critical, zone occupancy severity, motion sensitivity) to be configured
  without code changes, defaulting to the values in this specification.
- **FR-005**: The system MUST treat a finding produced by a module that errored, timed out, or
  returned very low confidence as `warning` at minimum, and MUST NEVER record it as `ok`.
- **FR-006**: The system MUST produce `HOLD` when any mandatory manual input is absent, and MUST
  name each absent input in the reasons.

**Pre-Launch Inspection (Story 1)**

- **FR-007**: The system MUST accept a single JPG, PNG, or WebP file of at most 10 MB by
  drag-and-drop or file picker, and MUST display a preview of the accepted image immediately.
- **FR-008**: The system MUST reject an unsupported type, an oversized file, or a corrupt file
  with a specific message, and MUST NOT start a run for a rejected upload.
- **FR-009**: The system MUST produce findings for each of: cracks or scratches, dents, surface
  or paint damage, dark or burn marks, fin symmetry expressed as an angle deviation in degrees,
  and missing bolts or parts (best-effort, and labelled as such in the finding message).
- **FR-010**: The system MUST render each finding's annotation overlay on the image, and MUST
  allow the engineer to toggle overlays on and off per module.
- **FR-011**: The system MUST raise a `warning` for a fin angle deviation greater than 3 degrees
  and a `critical` for one greater than 6 degrees, using the configured thresholds.

**Launchpad Monitor (Story 2)**

- **FR-012**: The system MUST let the user draw, edit, and delete a polygon danger zone over the
  frame, storing it with the run as normalized 0–1 coordinates alongside the source frame
  dimensions.
- **FR-013**: The system MUST re-render a saved zone in the same position at any display size.
- **FR-014**: The system MUST emit a `critical` finding for a person detected inside the zone,
  and MUST default to `critical` for a non-person object inside the zone with a configuration
  option to lower that to `warning`. A person outside the zone MUST NOT produce a zone finding.
- **FR-015**: The system MUST process a live webcam stream at a sustained rate of at least 2
  analyzed frames per second with end-to-end latency under 1.5 seconds on a 1280px laptop, and
  MUST accept an uploaded image or video file as an alternative source.
- **FR-016**: The system MUST display a live status banner showing `CLEAR`, `WARNING`, or
  `DANGER`, conveying the state with text and an icon as well as color, and MUST offer an
  optional audible alert that the user can enable and mute.
- **FR-017**: The system MUST record a chronological detection log for the run.

**Smoke, fire, leak, and motion cues (Story 3)**

- **FR-018**: The system MUST flag flame-like and smoke-like regions, and MUST flag abnormal
  motion in the vehicle base region by comparing consecutive frames.
- **FR-019**: The system MUST emit a `warning` for visible liquid pooling or a leak near the
  vehicle base, escalating to `critical` when a fire cue is also present in the same run.
- **FR-020**: Cue findings MUST carry the same fields and the same rendering as every other
  finding type.

**Agentic Safety Report (Story 4)**

- **FR-021**: The system MUST execute the checklist in the fixed order body, fins, launchpad
  area, weather and manual inputs, decision, and MUST stream the state of each step to the user
  as it happens.
- **FR-022**: The system MUST pause at the manual-inputs step, request exactly the missing
  mandatory inputs through an in-app form, and resume automatically on submission.
- **FR-023**: The system MUST validate manual input values against their allowed ranges and
  reject invalid values inline without submitting.
- **FR-024**: The final report MUST contain the verdict, the risk score, a pass/fail result for
  every checklist step, the reasons in priority order, the recommended actions, the annotated
  images, a timestamp, and the run id.
- **FR-025**: The report MUST state "Verdict computed by rules; explanation by AI" and MUST
  display the rule engine's verdict unchanged.
- **FR-026**: The system MUST produce a template-based report when the language model is
  unavailable or times out, containing the same verdict, risk score, checklist, and reasons, and
  MUST mark the narrative section as unavailable rather than omit it silently.
- **FR-027**: Narrative text and recommended actions MUST be written in hedged language, MUST NOT
  claim certification, and MUST NOT request or imply a change of verdict.

**Manual and context inputs**

- **FR-028**: The system MUST collect wind speed in metres per second, visibility
  (good/moderate/poor), precipitation (none/light/heavy), an area-cleared confirmation, and
  optional free-text notes, and MUST persist them with the run.
- **FR-029**: The system MUST evaluate wind above 10 m/s as `warning` and above 15 m/s as
  `critical`, poor visibility as `warning`, heavy precipitation as `warning`, and area not
  cleared as `critical`, using configured thresholds.
- **FR-030**: The four inputs named in FR-028, excluding notes, MUST be mandatory. Absence MUST
  produce `HOLD`.

**Dashboard, history, and sharing (Story 5)**

- **FR-031**: The dashboard MUST show the latest verdict, a risk score gauge, the checklist
  status, and the most recent runs.
- **FR-032**: The system MUST list past runs, MUST allow filtering by verdict, and MUST display
  the full report when a run is opened.
- **FR-033**: The system MUST export a report as a print or PDF view that remains legible in
  black and white, and MUST generate a read-only shareable link that exposes only that run's
  report and no controls.

**Demo mode (Story 6)**

- **FR-034**: The system MUST provide a "Load demo scenario" menu offering exactly three bundled
  scenarios — Normal (`GO`), Misaligned fin (`HOLD`), Person near pad (`NO-GO`) — each of which
  completes in one click and yields its expected verdict.
- **FR-035**: Demo scenarios MUST complete with the network disabled, and MUST use the
  template-based report path when no language model is reachable.
- **FR-036**: Demo scenarios MUST run the real inspection and rule pipeline, not pre-rendered
  results, so that a demonstrated verdict is the same code path as a real one.

**Honesty, privacy, and accessibility**

- **FR-037**: The system MUST display the disclaimer "Decision-support tool. Not a replacement
  for certified range safety." persistently wherever a verdict, risk score, or finding list is
  shown, on every screen enumerated in this specification.
- **FR-038**: No user-facing string in this feature may claim certification, regulatory approval,
  or guaranteed safety, and no finding message may state certainty that the detection did not
  produce.
- **FR-039**: The system MUST NOT transmit image data to any third party. Only a text summary of
  findings may be sent to the language model, and that summary MUST NOT contain image bytes,
  image locations, or any recoverable encoding of image content.
- **FR-040**: The system MUST store images and run data locally only, and MUST require no
  account, sign-in, or identity to use any capability in this feature.
- **FR-041**: The decision badge, live status banner, and every severity indicator MUST convey
  state using text and an icon in addition to color, and MUST remain legible at WCAG AA contrast
  in both the default dark theme and in black-and-white print.
- **FR-042**: The system MUST be fully operable by keyboard alone, and MUST disable all decorative
  animation when the user has requested reduced motion.
- **FR-043**: A measurement MUST be accompanied by its error margin whenever it falls within
  that margin of a decision threshold, so the report can show that the outcome is not
  distinguishable from the adjacent severity.

### Non-Functional Requirements

- **NFR-001**: A complete single-image inspection, from upload to verdict, MUST complete in under
  5 seconds on a 1280px laptop.
- **NFR-002**: A single monitored frame MUST be processed server-side in under 500 ms.
- **NFR-003**: No module failure may crash, hang, or abort a run; the run MUST always reach a
  verdict.
- **NFR-004**: The product MUST be usable at 1280px wide on a laptop, which is the primary
  target, and remain usable on a tablet.
- **NFR-005**: Image data MUST be held in memory or local storage only for the lifetime of the
  run, except where retention of a completed run's images is needed to re-open it from history.
- **NFR-006**: The product MUST run on a single laptop with no external service dependency other
  than the optional language model, and MUST remain fully demonstrable with that model
  unavailable.
- **NFR-007**: All three demo scenarios MUST be reproducible on a cold start with no prior runs
  in the store.

### UX Requirements

- **UX-001**: The default theme is a dark, mission-control aesthetic. A light theme is optional
  and not required for the MVP.
- **UX-002**: A large decision badge shows the verdict with a distinct icon and text for each of
  `GO`, `HOLD`, and `NO-GO`.
- **UX-003**: Decorative motion is permitted only for atmosphere — background effects, the risk
  score counter, and the live agent step timeline — and MUST NOT be used on the verdict badge,
  the finding list, severity indicators, or the disclaimer.
- **UX-004**: The five screens are: Landing / Dashboard, Pre-Launch Inspection, Launchpad
  Monitor, Safety Report, and History.
- **UX-005**: The Safety Report screen MUST present the agent timeline, the manual-input dialog,
  the final verdict, the checklist, the recommended actions, and the export controls.
- **UX-006**: The Launchpad Monitor screen MUST present a source selector, the zone editor, the
  live status banner, and the detection log.
- **UX-007**: The Pre-Launch Inspection screen MUST present the uploader, per-module overlay
  toggles, and the results with the annotated viewer.

### Constitution Alignment *(mandatory)*

- **Verdict source**: FR-001 and FR-002 are the only producers of a verdict. The rule engine
  consumes structured findings and manual-input rule results; the language model is invoked
  strictly after the verdict is fixed and is given no write path to it. Story 4 acceptance
  scenario 4 and FR-025 verify that the displayed verdict equals the rule engine's output.
  (Constitution 2.I)
- **Failure behaviour**: FR-005 covers module error, timeout, and low confidence, all of which
  yield at least `warning`. FR-006 and FR-030 cover absent mandatory inputs, which force `HOLD`.
  The "all modules failed" and "unusable frame" cases are listed under Edge Cases and also
  produce `HOLD`. The three-value severity scale (`ok`/`warning`/`critical`) is a superset of the
  constitution's two-value fail-safe rule and does not weaken it: the constitution's requirement
  is that failures never resolve to `ok`, which FR-005 preserves. (Constitution 2.II)
- **Finding fields**: FR-009 through FR-011 and FR-020 cover module, check id, severity,
  message, confidence, and metrics for every finding. Annotation overlays are produced by the
  visual modules — cracks, dents, damage, burn marks, fins, zone occupancy, and the cue
  detectors — and are toggled per module under FR-010. Zone occupancy and the manual-input rules
  carry metrics but no overlay, because they describe a region or a scalar rather than an object
  box. (Constitution 2.III)
- **Uncertainty wording**: FR-027 governs the narrative; FR-038 governs findings and all
  user-facing copy; FR-037 requires the disclaimer on every verdict-bearing screen. The hedged
  wording ("appears", "possible") is an explicit acceptance condition in Stories 1, 2, and 4, and
  FR-043 forces disclosure when a measurement sits inside its own error margin. (Constitution 2.IV)
- **Measurement provenance**: Every metric in a finding is produced by a detection step; the
  agent consumes those results and never computes an independent measurement. FR-036 prevents
  the demo path from bypassing this, since a mocked result would be a number with no tool behind
  it. (Constitution 2.V)
- **Contract impact**: This feature defines the complete request and response surface —
  inspection, monitoring, zone editing, run streaming, run retrieval, filtering, sharing, and
  report export. It is therefore the feature that establishes the interface contract rather than
  merely extending one, and the contract package must be generated from the API before the web
  application consumes it. Every later feature that changes the contract regenerates it. The
  credential used for narrative generation is held server-side only and never reaches the
  browser. (Constitution 3.I, 5.III)
- **Scope check**: This feature covers exactly the three modes named in the constitution —
  Pre-Launch Inspection, Launchpad Monitor, and AI Safety Report — with Dashboard, History, and
  Demo Mode as supporting surfaces of those modes, and exactly three demo scenarios. Thermal
  camera, drone inspection, vibration analysis, telemetry, and digital twin are explicitly
  deferred and appear nowhere in the requirements. Authentication and multi-tenancy are deferred
  by FR-040, which specifies no account or sign-in. (Constitution 6.I, 6.II)

### Key Entities

- **Run**: one inspection or monitoring session. Carries a run id, creation timestamp, mode, the
  source that produced it (uploaded image, video file, live stream, or bundled demo scenario),
  lifecycle status (running, paused awaiting input, completed, failed), the verdict, and the risk
  score. Owns findings, checklist steps, the danger zone, and the manual input set.
- **Finding**: one observation produced by one detection step. Carries the producing module, a
  stable check id, severity, human-readable message, confidence from 0 to 1, the measured
  metrics behind it, an optional error margin, and an optional annotation overlay reference.
  Belongs to a run; many findings per run.
- **Danger Zone**: a polygon of three or more points stored as normalized 0–1 coordinates plus
  the source frame dimensions it was defined against, so it can be re-rendered at any size.
  Belongs to a run.
- **Checklist Step**: one ordered stage of the safety checklist, carrying its position, status
  (pending, running, passed, failed, blocked awaiting input), the findings it produced, and any
  manual input it requires. A run has one of each of the five steps.
- **Manual Input Set**: the captured environmental and human-confirmed values for a run —
  wind speed, visibility, precipitation, area-cleared confirmation, and optional notes — each
  with a capture timestamp and the threshold rule that fired, if any.
- **Report**: the rendered and persisted outcome of a completed run: the verdict, the risk score,
  the ordered reasons, the recommended actions, the narrative and its availability state, the
  annotated images, a generation timestamp, the run id, and a share token if one was issued.
- **Demo Scenario**: a bundled, named, self-contained set of inputs and expectations — Normal
  expecting `GO`, Misaligned fin expecting `HOLD`, Person near pad expecting `NO-GO` — which runs
  through the real pipeline rather than replaying stored output.

---

## Assumptions and Deferred Decisions

The following were resolved with reasonable defaults rather than blocking on clarification, per
the request to propose defaults. Each is revisable without reopening the specification.

1. **Camera geometry for fin angle** — MVP measures the angle in the image plane and assumes a
   side-on view of the vehicle. There is no real-world camera calibration, so the reported angle
   is a projected angle and is labelled as such in the finding.
2. **Detection model choice** — deferred to `plan.md`. The binding constraint stated here is that
   the detector must run on a laptop CPU in real time; the specific weights are an architectural
   decision, and the product requires that the choice be swappable without touching the rule
   engine or the contract.
3. **Narrative model choice** — deferred to `plan.md`. The binding constraints are that it is
   swappable, that it receives a text summary only, and that its absence degrades to the
   template report rather than failing the run.
4. **Risk score formula** — deferred to `plan.md`, with the requirement that it is deterministic,
   reproducible from findings alone, bounded to 0–100, and incapable of influencing the verdict.
5. **Zone containment rule** — a detection counts as inside the zone when its bounding region
   overlaps the polygon at all. Chosen because under-reporting a person in a danger zone is the
   more dangerous error; the conservative bias is stated in the report.
6. **Threshold defaults are the starting configuration** — fin 3°/6°, wind 10/15 m/s, poor
   visibility warning, heavy precipitation warning, area-not-cleared critical, object-in-zone
   critical. All remain user-configurable under FR-004.
7. **Run retention** — completed runs and their images persist locally so history and sharing
   work. No automated expiry and no user-facing delete are in the MVP; this is a scope decision,
   not an oversight.
8. **Shareable links** — implemented as an unguessable read-only capability link, since
   authentication and multi-tenant access are explicitly out of scope. The link grants access to
   one report and no controls.
9. **Pre-Launch Inspection accepts still images only** — video is accepted by the Launchpad
   Monitor, which already streams frames. Adding video to the inspection flow would duplicate
   that path without adding safety value.
10. **Missing bolts and parts is best-effort** — labelled as such in the finding message,
    consistent with Constitution 2.IV. It does not by itself drive a critical verdict.
11. **Single-operator, single-machine deployment** — the product is designed for one launch team
    on one laptop. Concurrency beyond a few simultaneous browser views is out of scope.

---

## Out of Scope (MVP)

Thermal camera, drone inspection, vibration analysis, telemetry integration, digital twin,
authentication and multi-tenant support, ground-control integration, and any certified accuracy
claim. These are recorded here so that they are not introduced silently during implementation;
the constitution classifies thermal, drone, telemetry, and digital-twin work as deferred
(Constitution 6.II), and vibration analysis and ground-control integration are deferred by this
specification.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three demo scenarios produce their expected verdict in 10 out of 10 consecutive
  runs, from a cold start with no prior runs stored.
- **SC-002**: Fin angle measurements on the reference fixture set are within 1.5 degrees of the
  known value.
- **SC-003**: The live monitor detects a person entering the danger zone and shows the DANGER
  status within 1 second of the person entering the field of view.
- **SC-004**: An evaluator unfamiliar with the product can state the verdict and name at least one
  reason for it within 10 seconds of seeing the report, in 4 out of 5 trials.
- **SC-005**: A complete single-image inspection reaches a verdict in under 5 seconds on a 1280px
  laptop, in at least 9 out of 10 measured runs.
- **SC-006**: The live monitor sustains at least 2 analyzed frames per second with end-to-end
  latency under 1.5 seconds, with no dropped verdict state during a continuous 5-minute session.
- **SC-007**: An engineer completes a pre-launch inspection and reads the verdict without any
  training beyond the on-screen labels, in 4 out of 5 first-time trials.
- **SC-008**: With the network disabled, a demo scenario still completes and still yields its
  expected verdict in 10 out of 10 runs.
- **SC-009**: Every one of the five screens is usable at 1280px wide without horizontal scrolling
  of the primary content, and remains usable on a tablet.

### Safety & Honesty Outcomes

- **SH-001**: With any detection module forced to fail, the run still completes and the verdict is
  `HOLD` or `NO-GO` in 10 out of 10 trials, and is `GO` in 0 out of 10.
- **SH-002**: With every detection module forced to fail, no run crashes, hangs, or returns an
  error to the user in 10 out of 10 trials.
- **SH-003**: 100% of rendered findings display the producing module, check id, severity,
  human-readable message, confidence, and measured metrics.
- **SH-004**: No user-facing string asserts certification, approval, or guaranteed safety, and the
  disclaimer "Decision-support tool. Not a replacement for certified range safety." is present on
  all five screens in 10 out of 10 checks.
- **SH-005**: Every verdict, finding message, and narrative string passes a review confirming
  hedged wording and the absence of any claim of certainty beyond what the detection produced.
- **SH-006**: In 10 out of 10 trials, the verdict displayed in a report is byte-identical to the
  rule engine's independent output, including when the narrative step is forced to fail.
- **SH-007**: A fin measurement within its error margin of a threshold is accompanied by an
  explicit note that the outcome is not distinguishable from the adjacent severity, in 10 out of
  10 such cases.
- **SH-008**: With the narrative model disabled, the template report still contains the verdict,
  risk score, checklist, and ordered reasons, and marks the narrative as unavailable rather than
  omitting it, in 10 out of 10 trials.
- **SH-009**: No image data reaches any third party in 10 out of 10 network-inspection trials, and
  the payload sent to the narrative model contains no image bytes, image locations, or recoverable
  encoding of image content.
- **SH-010**: Every detection module has a test that runs against both a passing and a failing
  reference image, and each of the three demo scenarios has an end-to-end test asserting its
  expected verdict.
