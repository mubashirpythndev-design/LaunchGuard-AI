---
id: PHR-0001
title: Adopt LaunchGuard AI Safety Constitution
stage: constitution
date: 2026-09-29
surface: agent
model: opencode/big-pickle
feature: none
branch: main
user: mubashirpythndev-design
command: /sp.constitution
labels: [constitution, governance, safety, determinism, monorepo, test-discipline, spec-kit]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .specify/memory/constitution.md
  - .specify/templates/plan-template.md
  - .specify/templates/spec-template.md
  - .specify/templates/tasks-template.md
  - history/prompts/constitution/PHR-0001-adopt-launchguard-ai-safety-constitution.constitution.prompt.md
tests:
  - none — documentation-only change; no executable code touched
---

## Prompt

# LaunchGuard AI — Constitution

> Non-negotiable principles. Every spec, plan, task, and line of code must comply.
> Prompt to run first: `/constitution` (or paste this file as the agent's project rules).

## 1. Product identity
LaunchGuard AI is an **AI co-pilot for low-cost rocket safety inspection**. It inspects rocket hardware and launchpad conditions from images / video / webcam and returns a launch decision: **GO**, **HOLD**, or **NO-GO**, with reasons and recommended actions.

## 2. Safety principles (highest priority)
1. **Decisions are deterministic.** The GO / HOLD / NO-GO verdict is computed by a rule engine from structured findings. The LLM may *explain* and *recommend*; it may **never** upgrade a verdict (e.g. HOLD → GO). It may only agree with or escalate the rule engine.
2. **Fail safe.** Any module that errors, times out, or returns low confidence yields `severity: "warning"` (never `ok`). Missing mandatory checklist inputs → `HOLD`.
3. **Explainable.** Every finding carries: module, check id, severity, human-readable message, confidence (0–1), measured metrics, and (when visual) an annotation overlay.
4. **Honest uncertainty.** UI wording is "appears", "possible". Never claim certification. Show a persistent disclaimer: *"Decision-support tool. Not a replacement for certified range safety."*
5. **Computer vision proposes, agent coordinates.** The agent orchestrates CV tools; it never replaces them or invents measurements.

## 3. Architecture principles
1. **Two deployables, one contract.**
   - `apps/web` — Next.js (App Router) + TypeScript (strict) UI.
   - `apps/api` — Python 3.11 + FastAPI + OpenCV + YOLOv8 + agent.
   - The contract is `packages/contract` (OpenAPI → generated TS types + Zod schemas). The frontend never hand-writes API types.
2. **CV lives in Python only.** No OpenCV.js for core logic. The browser only captures, uploads, and renders.
3. **Agent tools are pure functions** `(input) -> Finding` with typed I/O, unit-tested on fixture images.
4. **Streaming first.** Agent progress is streamed to the UI (SSE) so each checklist step animates live.
5. **Stateless CV, stateful runs.** Runs, findings, reports persist in SQLite (swappable via SQLAlchemy).

## 4. Frontend principles
1. TypeScript `strict: true`, no `any`, no `@ts-ignore` without a comment explaining why.
2. UI primitives come from **shadcn/ui** (installed via CLI into `components/ui`). Do not hand-roll buttons, dialogs, tabs, tables, toasts, etc.
3. Interactive/animated flourishes come from **React Bits** (installed via the shadcn CLI registry into `components/react-bits`). Use them for atmosphere (background, hero text, counters, spotlight cards) — **never** on the decision-critical path where they could reduce legibility.
4. Styling: Tailwind CSS + CSS variables (shadcn theme). Dark, mission-control aesthetic by default; light theme optional.
5. Data fetching: TanStack Query. Forms: React Hook Form + Zod. State: local state + Zustand only for the live-monitor store.
6. Accessibility: WCAG AA contrast; decision state is conveyed by **text + icon + color**, never color alone; respect `prefers-reduced-motion` (disable React Bits animations).
7. Server Components by default; `"use client"` only where interaction/browser APIs are needed.

## 5. Quality bar
- Lint: ESLint + Prettier (web), Ruff + mypy (api). CI must pass.
- Tests: Vitest + React Testing Library (web), Playwright (one e2e per demo scenario), Pytest (api) with fixture images for the 3 demo scenarios.
- Every CV module must have a fixture test for a passing and failing image.
- No secrets in the repo. `.env.example` maintained. `OPENAI_API_KEY` server-side only.
- Small, reviewable commits: one task = one commit (Conventional Commits).

## 6. Scope discipline (hackathon)
- MVP = 3 modes (Pre-Launch Inspection, Launchpad Monitor, AI Safety Report) and 3 demo scenarios (GO / HOLD / NO-GO).
- Anything from "Future scope" (thermal, drone, telemetry, digital twin) is **out of scope** and must not leak into the MVP.
- Prefer a working, demoable vertical slice over breadth. If time is short, cut polish before cutting safety logic.

## 7. Definition of done
A task is done when: code compiles with no type errors, lint passes, tests for it pass, it is visible/usable in the UI (if user-facing), and it matches `spec.md` acceptance criteria.

---

## Response snapshot

Ratified `.specify/memory/constitution.md` at **v1.0.0** (unversioned template → 1.0.0; initial adoption, so MAJOR does not apply and MINOR understates a fully new principle set). All 15 template placeholders were resolved into 7 numbered sections + a **Governance** section (amendment procedure, SemVer policy, compliance review) that the supplied draft omitted but the template and command flow require. Every principle was rewritten from descriptive prose into normative MUST/MUST NOT/SHOULD language with a rationale line, preserving the author's intent — including one deliberate formalization: Principle 2.III now states that a finding missing its required fields MUST NOT be admitted into a decision, which is what makes "explainable" testable.

Propagation found one hard contradiction: `tasks-template.md` stated "Tests are OPTIONAL — only include them if explicitly requested", which directly violates Principle 5.II (fixture test per CV module, one Playwright e2e per demo scenario). That was corrected to REQUIRED, with sample task IDs renumbered and all sample paths realigned to `apps/web` / `apps/api` / `packages/contract` / `e2e`. `plan-template.md` had its `[Gates determined based on constitution file]` placeholder filled with 12 concrete gates (S1–S6, A1–A3, F1, Q1) and its generic single-project/frontend-backend/mobile trees replaced with the mandated monorepo. `spec-template.md` gained a Constitution Alignment block, honest-uncertainty constraints on acceptance scenarios, and SH-001–SH-005 safety success criteria. All 13 `.opencode/command/*.md` files and `opencode.md` were scanned: they reference the constitution only by path, so no edits were required.

## Outcome

- ✅ Impact: Project constitution ratified at v1.0.0 and four dependent templates synchronized. The single highest-value fix is removing the "tests are OPTIONAL" clause that would have permitted shipping untested CV modules in a safety tool. Three deferred TODOs recorded in the Sync Impact Report (scope ledger, low-confidence threshold value, agent-context tooling layout).
- 🧪 Tests: none — documentation-only change, no executable code touched. Validation performed instead: no remaining `[ALL_CAPS]` placeholder tokens, no trailing whitespace or tabs introduced, heading levels match the template (H1 title / H2 sections / H3 principles), ISO-8601 dates, version line consistent with the Sync Impact Report.
- 📁 Files: `.specify/memory/constitution.md` (rewritten), `.specify/templates/plan-template.md`, `.specify/templates/spec-template.md`, `.specify/templates/tasks-template.md`, plus this PHR.
- 🔁 Next prompts: `/sp.specify` for Pre-Launch Inspection (the P1 vertical slice) — it must resolve TODO(CONFIDENCE_FLOOR) by pinning the numeric low-confidence threshold, and TODO(SCOPE_LEDGER) by writing the explicit future-scope list.
- 🧠 Reflection: A constitution is only as strong as the weakest template it governs — the "tests are OPTIONAL" default in `tasks-template.md` would have quietly vetoed the project's own strongest safety principle, so reading dependent artifacts for *contradictions* (not just staleness) is the high-value part of the sync step.

## Evaluation notes (flywheel)

- Failure modes observed: (1) The prompt was re-sent with "try again" and no state was carried over, indicating a prior run aborted before writing any file — worth checking whether the constitution write is atomic. (2) The command flow directs the agent to run `.specify/scripts/bash/create-phr.sh`, but this repo only ships `.specify/scripts/powershell/*.ps1` and no `create-phr` script in any dialect, so the PHR had to be created agent-natively; the command's shell-first ordering is misleading on Windows/PowerShell hosts. (3) The command instructs the agent to read `.specify/templates/commands/*.md`, a path that does not exist here (commands live in `.opencode/command/`), and (4) the user-supplied draft had no Governance section, so ratification date could not be read from a prior version and had to be inferred as today.
- Graders run and results (PASS/FAIL): PASS — placeholder resolution; PASS — version/dates consistent with report; PASS — heading hierarchy preserved; PASS — normative language (no bare "should"); PASS — dependent templates synchronized; PASS — no unexplained bracket tokens; PASS — no trailing whitespace introduced.
- Prompt variant (if applicable): baseline.
- Next experiment (smallest change to try): Re-run `/sp.constitution` with a one-line amendment to the fail-safe threshold and confirm the version moves 1.0.0 → 1.0.1 (PATCH) while templates stay untouched — this tests that the versioning policy and the "which templates need re-sync" decision are actually driven by the change, not always re-triggered.
