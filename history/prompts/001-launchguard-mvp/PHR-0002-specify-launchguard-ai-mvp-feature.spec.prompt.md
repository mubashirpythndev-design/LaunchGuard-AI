---
id: PHR-0002
title: Specify LaunchGuard AI MVP Feature
stage: spec
date: 2026-09-29
surface: agent
model: opencode/big-pickle
feature: 001-launchguard-mvp
branch: 001-launchguard-mvp
user: mubashirpythndev-design
command: /sp.specify
labels: [specification, mvp, safety-verdict, computer-vision, acceptance-criteria, hackathon]
links:
  spec: specs/001-launchguard-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-launchguard-mvp/spec.md
  - specs/001-launchguard-mvp/checklists/requirements.md
  - history/prompts/001-launchguard-mvp/PHR-0002-specify-launchguard-ai-mvp-feature.spec.prompt.md
tests:
  - specification quality checklist — 16 items, all PASS after 1 correction pass
  - token scan for framework/model/vendor leakage in spec.md — 0 genuine matches
---

## Prompt

# LaunchGuard AI — Specification (WHAT and WHY, not HOW)

> Prompt to run: `/specify` — paste this file. Do not choose libraries here; that is `plan.md`.

## 1. Problem
Rocket development has costly, visually detectable failure points: cracks, dents, burn marks, misaligned fins, missing bolts, fuel/liquid leaks, smoke/fire, foreign objects and people in the danger zone. Industrial inspection systems are expensive; teams in emerging aerospace ecosystems (e.g. Pakistan) need an affordable alternative.

## 2. Vision
"An AI co-pilot for low-cost rocket safety inspection." A camera-based web app that inspects rocket hardware and the launchpad, reasons through a launch checklist like a safety officer, and outputs **GO / HOLD / NO-GO** with reasons and actions.

## 3. Users
| Persona | Need |
|---|---|
| Launch Engineer (primary) | Fast pre-launch visual inspection with a clear verdict and next actions |
| Range Safety Officer | Live pad monitoring; instant alert when someone/something enters the danger zone |
| Team Lead / Judge | Understand status at a glance; export/share report |

## 4. Verdicts and severity
- Finding severity: `ok` | `warning` | `critical`.
- Verdict rules (deterministic):
  - any `critical` → **NO-GO**
  - else any `warning`, or any mandatory input missing → **HOLD**
  - else → **GO**
- Risk score 0–100 derived from severities × confidence (formula in plan).

## 5. User stories & acceptance criteria

### US-1 Pre-Launch Inspection (P0)
As an engineer I upload a rocket image and get body and fin inspection results.
- AC1: Upload via drag-and-drop or file picker (JPG/PNG/WebP ≤ 10 MB); preview shown immediately.
- AC2: System reports findings for: cracks/scratches, dents, surface/paint damage, dark/burn marks, fin symmetry (angle deviation in degrees), missing bolts/parts (best-effort).
- AC3: Result page shows the image with annotation overlays (boxes/lines/angles) that can be toggled per module.
- AC4: Each finding lists severity, confidence, message, and metrics.
- AC5: Fin misalignment > 3° → warning; > 6° → critical (thresholds configurable).

### US-2 Launchpad Monitor (P0)
As a safety officer I define a danger zone and monitor an image, video file, or live webcam.
- AC1: I can draw/edit a polygon danger zone over the frame; it is saved with the run and normalized (0–1 coordinates).
- AC2: Persons detected inside the zone → **critical**. Non-person objects/tools inside the zone → **critical** (configurable to warning). Persons outside → ok.
- AC3: Live webcam analyzes ≥ 2 frames/second with visible latency < 1.5 s end-to-end on a laptop.
- AC4: A prominent live status banner switches between CLEAR / WARNING / DANGER with text + icon + color, plus an optional audible alert.
- AC5: Smoke/fire/leak cues are flagged (see US-3).

### US-3 Smoke / Fire / Leak / Abnormal Motion (P1)
- AC1: Color segmentation flags flame-like and smoke-like regions; frame differencing flags abnormal motion near the base region.
- AC2: Visible liquid pooling/leak near base flagged as warning (critical if combined with fire).
- AC3: Results appear as findings identical in shape to other modules.

### US-4 Agentic Safety Report (P0)
As an engineer I run the "Safety Officer" agent and watch it work through the checklist.
- AC1: Checklist steps run in order and stream live: (1) Inspect body → (2) Check fins → (3) Check launchpad area → (4) Check weather/manual inputs → (5) Generate decision.
- AC2: If mandatory manual inputs (wind speed, visibility, precipitation, personnel-cleared confirmation) are missing, the agent **pauses and asks** through an in-UI form, then resumes.
- AC3: Final report includes: verdict, risk score, pass/fail checklist, ordered reasons, recommended actions, annotated images, timestamp, and run id.
- AC4: The narrative and recommendations are LLM-written but the verdict equals the rule engine's output; the report shows "Verdict computed by rules; explanation by AI".
- AC5: If the LLM is unavailable, a template-based report is still produced.

### US-5 Mission Dashboard & History (P1)
- AC1: Dashboard shows the latest verdict, risk gauge, checklist status, and recent runs.
- AC2: History lists past runs with filter by verdict; opening one shows the full report.
- AC3: Report can be exported as PDF/print view and a shareable link (read-only).

### US-6 Demo mode (P0 for hackathon)
- AC1: A "Load demo scenario" menu provides 3 bundled scenarios: Normal (GO), Misaligned fin (HOLD), Person near pad (NO-GO). Each yields its expected verdict in one click, reliably, offline.

## 6. Manual/context inputs (checklist step 4)
Wind speed (m/s), visibility (good/moderate/poor), precipitation (none/light/heavy), area cleared confirmation (bool), optional notes. Rules: wind > 10 m/s → warning, > 15 → critical; visibility poor → warning; heavy precipitation → warning; area not cleared → critical. (Thresholds configurable.)

## 7. Non-functional requirements
- Performance: single-image inspection < 5 s; monitor frame < 500 ms server time.
- Reliability: module failure never crashes a run; it degrades to warning.
- Privacy: images stored locally only; no third-party upload except LLM text summary (no images sent to the LLM in MVP).
- Accessibility: keyboard navigable, AA contrast, reduced-motion support.
- Responsive: usable on 1280px laptop (primary) and tablet.

## 8. UX requirements
- Mission-control dark theme; large decision badge (GO green / HOLD amber / NO-GO red) with icon + text.
- Animated but restrained: interactive background, animated counters for risk score, live agent step timeline, spotlight-hover cards for module results.
- Persistent safety disclaimer footer.

## 9. Screens
1. **Landing / Dashboard** — hero, latest status, quick actions, recent runs.
2. **Pre-Launch Inspection** — uploader, module toggles, results with annotated viewer.
3. **Launchpad Monitor** — source selector (image/video/webcam), zone editor, live status banner, detection log.
4. **Safety Report** — agent timeline, manual-input dialog, final verdict, checklist, actions, export.
5. **History** — table + filters.

## 10. Out of scope (MVP)
Thermal camera, drone inspection, vibration analysis, telemetry, digital twin, auth/multi-tenant, ground-control integration, certified accuracy claims.

## 11. Success metrics (hackathon)
- All 3 demo scenarios produce the expected verdict 10/10 runs.
- Fin angle error ≤ 1.5° on the fixture set.
- Live monitor detects a person entering the zone within 1 s.
- Judge can understand the verdict and reasons in < 10 s.

## 12. Open questions (agent should propose defaults, not block)
- Which YOLO weights? (default: `yolov8n.pt`)
- Which LLM? (default: OpenAI `gpt-4o-mini`, pluggable)
- Camera calibration for real-world angle? (MVP: image-plane angle only, assume side-on view) 

---

## Response snapshot

Created branch `001-launchguard-mvp` and wrote `specs/001-launchguard-mvp/spec.md` (640 lines) plus `checklists/requirements.md`. Short name `launchguard-mvp`; number 1, since the repository had no remote, no `specs/` directory, and only `main`.

The specification reorganises the source description into the template's mandatory shape without discarding any of it: 6 user stories re-ordered into dependency order and renumbered P1–P6 with each heading retaining its `source US-n` identifier, 30 edge cases grouped by failure class, 43 functional requirements, 7 non-functional requirements, 7 UX requirements, 9 measurable success criteria, 10 safety and honesty outcomes, 7 key entities, and 11 documented assumptions. Zero `[NEEDS CLARIFICATION]` markers, because the source explicitly asked for defaults rather than blocking and supplied defaults for all three open questions — those three (detector weights, narrative model, camera calibration) are recorded as deferred to `plan.md` with only their binding constraints stated here, so the spec stays implementation-neutral while the author's preferences survive for the planning phase.

Three substantive additions beyond transcription, each argued in the checklist: (1) FR-003 makes the risk score explicitly **advisory** — it is displayed but MUST NOT alter the verdict, closing a path by which a display value could become a decision; (2) FR-043 and SH-007 require a measurement to be flagged when it falls within its own error margin of a threshold, because the 1.5° fin accuracy target (SC-002) against a 3° warning threshold (FR-011) makes a genuine 3.0° misalignment indistinguishable from acceptable — this cannot be specified away, so it is disclosed rather than hidden; (3) FR-036 requires demo scenarios to run the real pipeline instead of replaying stored output, so a demonstrated verdict exercises the same code path as a real one.

The one validation failure found and fixed: the Constitution Alignment section named a specific vendor credential while stating the server-side-only rule, which is an implementation detail in a WHAT/WHY document. Rewritten to name only the constraint.

## Outcome

- ✅ Impact: Feature `001-launchguard-mvp` specified and ready for planning. All 16 quality checklist items pass. The specification is the first artifact to bind the constitution's safety principles to testable requirements, and it does so through FR-001/FR-005/FR-006 (verdict isolation, fail-safe, mandatory inputs), FR-037/FR-038/FR-027 (disclaimer and hedged wording), FR-036 (demo paths run the real pipeline), and FR-043 (error-margin disclosure).
- 🧪 Tests: no executable code. Validation performed: placeholder scan clean (0 hits), clarification-marker count 0, implementation-leak scan clean (0 genuine matches after correcting the one vendor credential; apparent `SSE` hits were substrings of "expre**sse**d" and "a**sse**rting"), 640 lines with no trailing whitespace.
- 📁 Files: `specs/001-launchguard-mvp/spec.md`, `specs/001-launchguard-mvp/checklists/requirements.md`, `history/prompts/001-launchguard-mvp/` (route directory), this PHR.
- 🔁 Next prompts: `/sp.plan` to produce `plan.md` — it must resolve the three deferred decisions (detector weights, narrative model, risk-score formula), fill the Technical Context fields the constitution fixes, and pass the 12 Constitution Check gates now written into `plan-template.md`. Then `/sp.tasks`.
- 🧠 Reflection: The specification's hardest problem was not describing the six stories but resisting the pull to keep the three "open questions" concrete. Naming `yolov8n.pt` and `gpt-4o-mini` would have been easier and would have read as more complete, but it would have made the spec a plan in disguise and given `/sp.plan` nothing left to decide — deferring them while stating their binding constraints preserved the author's intent and kept the planning stage meaningful.

## Evaluation notes (flywheel)

- Failure modes observed: (1) `.specify/scripts/powershell/create-new-feature.ps1` crashed partway on Windows PowerShell 5.1 at `Join-Path $repoRoot 'history' 'prompts' $branchName` — `Join-Path` takes only two positional arguments before PowerShell 7's `-AdditionalChildPath`, so the branch and `spec.md` were created but the `history/prompts/<branch>/` directory and the JSON output never happened. The correct recovery was to create the directory manually and **not** re-run the script, since the flow permits exactly one invocation per feature; a naive retry would have created a duplicate branch. (2) The flow's instruction to pass the full multi-line description as a command argument is unsafe on PowerShell — the description contains backticks (escape characters), pipe characters in markdown tables, and non-ASCII em-dashes and arrows. I passed a faithful one-line summary plus explicit `-ShortName` and `-Number` instead, which is functionally identical because the script uses the description only for name generation and that was overridden. (3) The script's own `-Json` switch was not honoured as documented in the flow's PowerShell example, which showed `-Json` in a position that would have bound to the wrong parameter.
- Graders run and results (PASS/FAIL): PASS — spec contains no framework, model, library, vendor, or language name; PASS — zero unresolved template placeholders; PASS — zero NEEDS CLARIFICATION markers, within the limit of 3; PASS — all 6 stories carry independent-test statements; PASS — Constitution Alignment section complete against all 7 mandatory prompts; PASS — success criteria measurable and technology-agnostic; PASS — out-of-scope list matches the constitution's deferred list plus this spec's additions; PASS — PHR has no unresolved placeholders and is routed to the stage-matching directory.
- Prompt variant (if applicable): baseline, immediately following PHR-0001 (constitution stage) on the same feature thread.
- Next experiment (smallest change to try): Run `/sp.plan` and check that the Technical Context block and the 12 Constitution Check gates are actually derivable from this spec plus the constitution without re-litigating anything — in particular that FR-043's error-margin requirement surfaces as a concrete data field in the plan's data model, since that is the requirement most likely to be silently dropped as "nice to have".
