# LaunchGuard AI: Pitch & Demonstration Plan

> **An AI co-pilot for low-cost rocket safety inspection.**
> *Decision-support tool. Not a replacement for certified range safety.*

---

## Executive Summary

Suborbital research initiatives, university rocketry teams (Spaceport America Cup, ESRA), and emerging commercial space startups operate under extreme resource constraints. Unlike government launch complexes with multi-million-dollar safety infrastructure, low-cost launch operators rely heavily on manual checklists and visual spot-checks under high time pressure.

Overlooked structural defects — such as aerodynamic fin cant deviations or hairline airframe cracks — and accidental pad intrusions account for preventable launch failures, catastrophic pad fires, and regulatory grounding.

**LaunchGuard AI** delivers an operational AI safety co-pilot that combines computer vision defect detection, live exclusion zone monitoring, and structured agentic checklists into an offline-first mission control console.

---

## Core Value Propositions

### 1. Vision Proposes, Rules Decide, AI Explains
Probabilistic models must never decide flight safety. In LaunchGuard AI, a deterministic Python rule engine (`apps/api/rule_engine/`) holds sole authority over the **GO / HOLD / NO-GO** verdict. The language model explains findings and suggests actions, but cannot alter, upgrade, or bypass safety rules.

### 2. Zero-Network, Single-Laptop Deployment
A launch pad at a desert dry lakebed rarely has reliable 5G or cloud connectivity. LaunchGuard AI runs entirely locally on a single laptop with SQLite and local OpenCV/YOLO models. If the language model is unreachable, the system falls back seamlessly to deterministic template-generated reports with zero downtime.

### 3. Fail-Safe and Unforgiving Invariants
Any sensor error, timeout, or low-confidence detection automatically degrades to a `warning` severity and can never yield an `ok`. Missing mandatory environmental inputs (wind velocity, visibility, precipitation, pad clearance) force at least `HOLD`; a critical defect still requires `NO-GO`.

### 4. Privacy & ITAR / Export Control Conscious
Zero frame bytes or imagery ever leave the operator's machine. Language models receive only sanitized, anonymized numeric finding metrics and check IDs.

---

## 3-Scenario Live Demo Walkthrough (3 Minutes)

The demonstration proves the complete pipeline end-to-end using the canonical order: **GO -> HOLD -> NO-GO**.

### Phase 1: Nominal Flight Vehicle -> Verdict: GO
- **Action**: Operator loads the bundled "Nominal Flight Vehicle" scenario.
- **Under the Hood**:
  - `cv.body` verifies fuselage skin integrity and surface contrast.
  - `cv.fins` measures projected left/right leading-edge asymmetry from visible segments.
  - `cv.zone` confirms launchpad exclusion perimeter is clear.
  - Manual inputs verify wind at 3.5 m/s, good visibility, and no precipitation.
- **Judge Impact**: Green **GO** badge renders with a low risk score (< 30), highlighting nominal pre-flight telemetry.

### Phase 2: Asymmetric Fin Mount -> Verdict: HOLD
- **Action**: Operator loads "Fin Mount Misalignment" scenario.
- **Under the Hood**:
  - `cv.fins` measures a discrepancy between detected fin leading-edge inclinations.
  - The measurement strictly exceeds the 3.0 deg warning threshold while remaining within the 6.0 deg critical limit.
  - The rule engine fires a `warning` severity finding with an interactive ARC overlay.
- **Judge Impact**: Amber **HOLD** badge displays with clear advisory recommendations: *"Manual fin trim inspection recommended before flight operations resume."* Shows how minor structural anomalies are caught before liftoff.

### Phase 3: Exclusion Zone Intrusion -> Verdict: NO-GO
- **Action**: Operator loads "Pad Exclusion Zone Breach" scenario.
- **Under the Hood**:
  - Technician figure is detected inside the marked danger zone coordinates.
  - Zone geometry containment evaluator immediately triggers a `critical` severity finding.
  - Real-time audible alert capability and DANGER banner activate.
- **Judge Impact**: Red **NO-GO** badge displays with high risk score (>= 70) and mandatory remediation requirement: *"Clear the launch exclusion zone and confirm with range safety before proceeding."* Demonstrates life-safety protection.

---

## Golden Reference Extension Demo (Feature 002)

- Register a vehicle with four designated baseline views. For the synthetic demo,
  use `rocket_golden_reference.jpg` in each enrollment slot.
- Submit `rocket_current_intact.jpg` for Front, Right, and Left, and
  `rocket_current_cracked.jpg` for Back. Both retain the baseline livery; only the
  cracked illustration contains the new defect.
- Open Back evidence in the saved report. Wipe the baseline/current slider, toggle
  red difference contours, and display the difference map. OpenCV runs in Python;
  the browser only captures and displays images.
- Explain the invariant: a critical finding on one angle forces NO-GO for the
  entire run. No averaging across views and no LLM override.
- Compare with the unchanged fixture: reference OK is not launch authorization.
  Manual inputs and all other findings still participate in the verdict.

These illustrations demonstrate the pipeline, not certified defect sensitivity,
factory certification, physical 360-degree coverage, or reliable field performance.
Alignment failures remain degraded warnings. Real deployment requires representative
hardware imagery, controlled capture procedures, and independent safety validation.

## Market & Deployment Horizon

- **Primary Target**: Over 150 collegiate rocket engineering teams competing globally and commercial micro-launch startups.
- **Hardware Footprint**: Standard field laptop with web browser and USB / RTSP range cameras.
- **Safety Boundary**: Demonstration software, not a certified safety system or evidence of regulatory compliance.
