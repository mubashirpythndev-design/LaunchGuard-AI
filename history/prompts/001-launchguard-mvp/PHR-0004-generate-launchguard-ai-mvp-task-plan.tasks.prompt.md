---
id: PHR-0004
title: Generate LaunchGuard AI MVP Task Plan
stage: tasks
date: 2026-09-29
surface: agent
model: opencode/big-pickle
feature: 001-launchguard-mvp
branch: 001-launchguard-mvp
user: mubashirpythndev-design
command: /sp.tasks
labels: [tasks, task-breakdown, user-stories, traceability, constitution-check, test-obligations, hackathon-scheduling]
links:
  spec: specs/001-launchguard-mvp/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-launchguard-mvp/tasks.md
  - specs/001-launchguard-mvp/plan.md
  - specs/001-launchguard-mvp/quickstart.md
  - AGENTS.md
tests:
  - id: tasks-structure
    kind: static-check
    command: "custom PowerShell: 145 task lines, IDs contiguous T001-T145, no duplicates, no malformed IDs"
    result: pass
  - id: story-tag-placement
    kind: static-check
    command: "custom PowerShell: every task carrying [USn] sits inside a User Story phase"
    result: pass
  - id: path-presence
    kind: static-check
    command: "custom PowerShell: every task names at least one exact file path"
    result: pass
  - id: relative-links
    kind: static-check
    command: "custom PowerShell: ./plan.md, ./research.md, ./spec.md all resolve"
    result: pass
  - id: template-conformance
    kind: static-check
    command: "19 required tasks-template.md sections present"
    result: pass
  - id: requirement-traceability
    kind: static-check
    command: "custom PowerShell: 76/76 spec requirements cited in tasks.md (43 FR, 7 NFR, 7 UX, 9 SC, 10 SH)"
    result: pass
  - id: matrix-integrity
    kind: static-check
    command: "custom PowerShell: 0 dangling T-refs; 48 uncited tasks all declared as infrastructure"
    result: pass
  - id: forbidden-patterns
    kind: static-check
    command: "grep for DecryptedText / ClickSpark / openapi-typescript / apps\/contract / asyncio.Event"
    result: pass
  - id: phase-range-agreement
    kind: static-check
    command: "custom PowerShell: 8-Hour Order table ranges match actual phase boundaries"
    result: pass
---

## Prompt

Generate an actionable, immediately executable `tasks.md` for the LaunchGuard AI MVP, organized by
user story and prioritized by story priority rather than by technical layer.

Requirements the generated task list must satisfy:

- Read `plan.md` and `spec.md` as required inputs, plus `research.md`, `data-model.md`, and
  `contracts/` as optional context.
- Conform to the repository's customized `tasks-template.md`: exact checklist format
  `- [ ] [TaskID] [P?] [Story?] Description with file path`, mandatory tests per Constitution
  5.II, and the canonical monorepo path conventions.
- `.specify/memory/constitution.md` is non-negotiable. Any task that would violate a MUST must be
  resolved, not weakened.
- Organize by user story in spec priority order: US1 (P1), US2 (P2), US4 (P3), US6 (P4), US5 (P5),
  US3 (P6).
- Preserve the supplied 8-hour hour-by-hour scheduling shape as a separate agenda view, clearly
  distinguished from the dependency order.
- Every task must name an exact file path. One task equals one commit.
- Provide Dependencies & Execution Order, Parallel Opportunities, a Parallel Example, an
  Implementation Strategy, and a requirements traceability matrix.

Standing project constraints the task list must respect:

- The GO / HOLD / NO-GO verdict is computed **only** by `apps/api/rule_engine/`, which imports
  nothing from `cv/` or `agent/`. The language model explains and recommends; it never alters a
  verdict, and its output schema has no field to write one into.
- A module that errors, times out, or scores below `MIN_CONFIDENCE_FOR_OK` (0.35) yields
  `warning`, never `ok`.
- All computer vision lives in `apps/api`. No OpenCV.js, no browser-side detection.
- `apps/web` declares no API types of its own. `lib/schemas.ts` re-exports `@launchguard/contract`
  only; `packages/contract/src` is generated and must never be hand-edited.
- React Bits are atmosphere only. Never on the verdict badge, finding list, severity indicators,
  or disclaimer.
- `OPENAI_API_KEY` is server-side only. Never a `NEXT_PUBLIC_*` variable.
- The disclaimer "Decision-support tool. Not a replacement for certified range safety." is visible
  on all five screens.
- Three demo scenarios must yield GO / HOLD / NO-GO: `normal`, `misaligned_fin`,
  `person_near_pad`.

## Response snapshot

Wrote `specs/001-launchguard-mvp/tasks.md` — 145 tasks, T001 through T145, contiguous, across nine
phases:

- **Phase 1 Setup (T001–T013)** — pnpm workspace, `apps/web` scaffold, `apps/api` layout,
  `packages/contract` + `@hey-api/openapi-ts` config, `scripts/export_openapi.py`, `.env.example`,
  Ruff/mypy config, shadcn, React Bits install, demo fixtures, `conftest.py`, GitHub Actions CI.
- **Phase 2 Foundational (T014–T051)** — the blocking floor: the rule engine
  (`types.py`/`config.py`/`registry.py`/`verdict.py`/`risk.py`/`manual.py`), persistence (8 tables),
  the SSE substrate with `run_events` persistence and `Last-Event-ID` replay, the checkpointer
  lifespan, the Next.js SSE proxy, and 11 foundational test tasks including the rule-engine import
  isolation guard.
- **Phases 3–8 User Stories** — US1 (T052–T074), US2 (T075–T092), US3 (T093–T098), US4
  (T099–T116), US5 (T117–T128), US6 (T129–T135), each with a separate tests block ahead of its
  implementation block, per the template.
- **Phase 9 Polish (T136–T145)** — accessibility, hedging/disclaimer audit, secrets audit, React
  Bits boundary audit, performance, coverage gaps, `README.md`, `PITCH.md`.

Three deviations from the outline's suggestions were made and documented in a table at the top of
the file, each with its Constitution rationale:

1. `agent/rules.py` → `rule_engine/verdict.py` importing nothing from `cv/` or `agent/`
   (Constitution 2.I, research R6).
2. `DecryptedText` verdict reveal → static text + icon + colour (Constitution 4.III, UX-003, R3).
3. `openapi-typescript` for types **and** Zod → `@hey-api/openapi-ts` with the Zod v4 plugin, since
   `openapi-typescript` emits types only and hand-written Zod would be exactly the drift
   Constitution 3.I forbids (R1).

Also added: a `Path Conventions` section fixing the layout to `apps/web`, `apps/api`,
`packages/contract`, `e2e`, `scripts`, `specs/`; a `Requirements Traceability` matrix covering all
76 spec requirements; a `Parallel Team Strategy`; and a `Hackathon 8-Hour Order` table mapped onto
the final task IDs with an explicit cut list.

Before this run, corrected a path inconsistency introduced earlier in the session: `plan.md`'s
source tree, `quickstart.md`, and `AGENTS.md` referred to `apps/contract/` where Constitution 3.I
and `research.md` mandate `packages/contract/`. Also normalized the OpenAPI export script to
`scripts/export_openapi.py` at the repo root rather than `apps/api/scripts/`.

## Outcome

- ✅ Impact: Produced the final implementation plan for 001-launchguard-mvp — 145 ordered,
  path-specific, commit-sized tasks that unblock implementation. All three Constitution-violating
  suggestions in the outline were corrected rather than implemented. Fixed a `packages/contract`
  path drift that would have sent scaffolding to the wrong directory. Verified all 76 spec
  requirements are traceable to at least one task with zero dangling task references.
- 🧪 Tests: No code was written, so no runtime tests were executed. Validation was static, using
  throwaway PowerShell checkers (since `.specify/scripts/bash/create-phr.sh` is absent and no test
  harness exists yet): task-ID contiguity and uniqueness, story-tag phase placement, per-task file
  path presence, relative-link resolution, `tasks-template.md` section conformance, 76/76
  requirement traceability, matrix reference integrity, forbidden-pattern grep, and agreement
  between the 8-Hour Order table and actual phase boundaries. All passed. The checkers were
  deleted after use so no scaffolding is committed.
- 📁 Files: Created `specs/001-launchguard-mvp/tasks.md` (53 KB). Modified
  `specs/001-launchguard-mvp/plan.md` (tree block and layout rationale), `quickstart.md` (tree,
  generate commands, drift check), and `AGENTS.md` (two manual lines). Nothing committed.
- 🔁 Next prompts: `/sp.implement` to execute Phase 1 + Phase 2, or `/sp.analyze` if a
  requirements gap surfaces during implementation.
- 🧠 Reflection: Three errors in my own work were caught only because I verified rather than
  assumed, and each was a different class of error. I wrote a "requirements traceability matrix"
  citing SC-010, which does not exist — the spec has 9 success criteria, not 10, and I had
  invented one to make the numbers look tidy; the count check caught the fabricated row. My 8-Hour
  Order table carried task IDs from the user's original outline numbering after I had renumbered
  the file, so the table pointed at unrelated tasks; a phase-range check caught it. And two
  separate PowerShell validators produced false results — one from a malformed regex character
  class, one from omitting `RegexOptions.Multiline` on a whole-file `^` anchor — which briefly
  reported 0% traceability. The lesson is that a validator I wrote in the same sitting as the data
  it validates is itself untrusted until its output is cross-checked by a different method. The
  fabricated SC-010 is the most serious of the three: it was a claim of completeness that a reader
  would reasonably trust, and it was false.

## Evaluation notes (flywheel)

- Failure modes observed:
  - **Fabricated traceability row.** Invented `SC-010` to round out the success-criteria count.
    The spec defines 9 (SC-001..SC-009). Caught by diffing matrix row count against a
    regex extraction of the spec.
  - **Stale cross-references after renumbering.** The 8-Hour Order table and the Implementation
    Strategy referenced the outline's original T001–T094 IDs after the file was renumbered to
    T001–T145, so entries pointed at the wrong tasks. Caught by extracting actual phase task ranges
    and comparing.
  - **False negative from a broken validator.** Two of my PowerShell checkers were themselves buggy
    (a malformed `[1-6\]` character class; a missing `RegexOptions.Multiline` making a `^` anchor
    match only the start of the whole file). One reported 0% traceability when true coverage was
    100%. Diagnosed by testing the regex directly against a known line.
  - **UTF-8 read as ANSI.** `Get-Content` mangled em-dashes and en-dashes, corrupting pattern
    matching. Fixed by reading with `[System.IO.File]::ReadAllLines` and an explicit UTF-8 encoding.
  - **Structural regression from a careless edit.** An edit restoring `## Notes` also silently
    deleted the header and misplaced the team-strategy section. Caught by re-extracting all
    headings and comparing against the template's required section list.
- Graders run and results (PASS/FAIL):
  - Task ID contiguity, uniqueness, format — PASS
  - Story tags confined to User Story phases — PASS
  - Every task names an exact file path — PASS (fixed 4 tasks: T137, T139, T141, T144)
  - Malformed story marker on T082 (`[US1→US2]`) — FIXED to `[US2]`
  - Relative Markdown links resolve — PASS
  - `tasks-template.md` section conformance (19 sections) — PASS (added missing
    `Path Conventions` and `Parallel Team Strategy`)
  - Requirement traceability — PASS 76/76, after removing the fabricated SC-010 row
  - Matrix integrity (no dangling T-refs) — PASS
  - Forbidden patterns (DecryptedText, ClickSpark, openapi-typescript, apps/contract, asyncio.Event
    as an implementation choice) — PASS; all remaining hits are explicit prohibitions or the
    documented deviations table
  - Phase-range agreement for the 8-Hour Order table — PASS (rewritten against real ranges)
  - `packages/contract` path consistency across plan/quickstart/AGENTS — PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Before writing any large generated artifact, extract the
  authoritative identifier set from the source document first and print it, so counts and IDs are
  known before a matrix is drafted. Both fabrication errors (SC-010, stale T-IDs) would have been
  prevented by that one step. Secondarily, prefer a real test harness over ad-hoc throwaway
  validators even for static checks, so a validator bug surfaces as a failing test rather than as
  a false all-clear.
