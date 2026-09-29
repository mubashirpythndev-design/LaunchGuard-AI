---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/
**Constitution**: `.specify/memory/constitution.md` (v1.0.0) — every task MUST comply. If a task
cannot comply, resolve the conflict in `spec.md` or `plan.md` first; do not weaken the task.

**Tests**: **REQUIRED, not optional** (Constitution 5.II — Test Obligations). Every task list
MUST include test tasks. Minimum obligations:

- Every CV module gets a fixture test with at least one **passing** and one **failing** image.
- Every e2e demo scenario (GO, HOLD, NO-GO) gets a Playwright spec.
- Web code touched by a story gets Vitest + React Testing Library coverage.
- API code touched by a story gets Pytest coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Constitution 3.I (Two Deployables, One Contract) fixes the layout. These paths are mandatory;
do not invent a single-project, generic `frontend/` + `backend/`, or mobile structure.

- **Web**: `apps/web/app/`, `apps/web/components/ui/`, `apps/web/components/react-bits/`,
  `apps/web/lib/`, `apps/web/stores/`, `apps/web/tests/`
- **API**: `apps/api/app/`, `apps/api/agent/`, `apps/api/cv/`, `apps/api/rule_engine/`,
  `apps/api/db/`, `apps/api/tests/{unit,contract,fixtures/images}/`
- **Contract**: `packages/contract/openapi.json`, `packages/contract/src/` — **generated only**;
  never hand-write or hand-edit these files
- **E2E**: `e2e/` — one Playwright spec per demo scenario
- **Docs**: `specs/[###-feature-name]/`

Paths shown below are illustrative only — rewrite every sample task with the real path for this
feature.

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /sp.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup SQLite + SQLAlchemy schema and migrations framework
- [ ] T005 [P] Generate `packages/contract` (OpenAPI → TS types + Zod schemas) from `apps/api`
- [ ] T006 [P] Configure linting: ESLint + Prettier (web), Ruff + mypy (api)
- [ ] T007 [P] Configure CI to run lint, typecheck, and tests
- [ ] T008 Create base models/entities that all stories depend on (Run, Finding, Decision)
- [ ] T009 Implement the deterministic rule engine skeleton (GO / HOLD / NO-GO) with no LLM path
- [ ] T010 Setup environment configuration management and `.env.example`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (REQUIRED by Constitution 5.II) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Pytest contract test for [endpoint] in `apps/api/tests/contract/test_[name].py`
- [ ] T012 [P] [US1] Pytest unit test for [agent tool] incl. passing + failing fixture images in `apps/api/tests/fixtures/images/`
- [ ] T013 [P] [US1] Vitest + RTL test for [component] in `apps/web/tests/test_[name].test.tsx`
- [ ] T014 [P] [US1] Playwright e2e for this story's demo scenario in `e2e/[scenario].spec.ts`

### Implementation for User Story 1

- [ ] T015 [P] [US1] Create [Entity1] model in `apps/api/db/models/[entity1].py`
- [ ] T016 [P] [US1] Create [Entity2] model in `apps/api/db/models/[entity2].py`
- [ ] T017 [US1] Implement [CV tool] as a pure `(input) -> Finding` function in `apps/api/cv/[name].py` (depends on T015, T016)
- [ ] T018 [US1] Implement [endpoint/feature] in `apps/api/app/[name].py`
- [ ] T019 [US1] Regenerate `packages/contract` from the updated OpenAPI document
- [ ] T020 [US1] Add validation and error handling — every failure path yields `severity: "warning"`
- [ ] T021 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (REQUIRED by Constitution 5.II) ⚠️

- [ ] T022 [P] [US2] Pytest contract test for [endpoint] in `apps/api/tests/contract/test_[name].py`
- [ ] T023 [P] [US2] Pytest unit test for [agent tool] incl. passing + failing fixture images in `apps/api/tests/fixtures/images/`
- [ ] T024 [P] [US2] Vitest + RTL test for [component] in `apps/web/tests/test_[name].test.tsx`
- [ ] T025 [P] [US2] Playwright e2e for this story's demo scenario in `e2e/[scenario].spec.ts`

### Implementation for User Story 2

- [ ] T026 [P] [US2] Create [Entity] model in `apps/api/db/models/[entity].py`
- [ ] T027 [US2] Implement [Service] in `apps/api/agent/[service].py`
- [ ] T028 [US2] Implement [endpoint/feature] in `apps/api/app/[name].py`
- [ ] T029 [US2] Regenerate `packages/contract` from the updated OpenAPI document
- [ ] T030 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (REQUIRED by Constitution 5.II) ⚠️

- [ ] T031 [P] [US3] Pytest contract test for [endpoint] in `apps/api/tests/contract/test_[name].py`
- [ ] T032 [P] [US3] Pytest unit test for [agent tool] incl. passing + failing fixture images in `apps/api/tests/fixtures/images/`
- [ ] T033 [P] [US3] Vitest + RTL test for [component] in `apps/web/tests/test_[name].test.tsx`
- [ ] T034 [P] [US3] Playwright e2e for this story's demo scenario in `e2e/[scenario].spec.ts`

### Implementation for User Story 3

- [ ] T035 [P] [US3] Create [Entity] model in `apps/api/db/models/[entity].py`
- [ ] T036 [US3] Implement [Service] in `apps/api/agent/[service].py`
- [ ] T037 [US3] Implement [endpoint/feature] in `apps/api/app/[name].py`
- [ ] T038 [US3] Regenerate `packages/contract` from the updated OpenAPI document

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in `docs/`
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Fill coverage gaps in `apps/api/tests/unit/` and `apps/web/tests/`
- [ ] TXXX Security hardening — confirm `OPENAI_API_KEY` never reaches the browser bundle
- [ ] TXXX Accessibility pass: WCAG AA contrast, text + icon + colour on every verdict, `prefers-reduced-motion` honoured
- [ ] TXXX [P] Verify the "Decision-support tool. Not a replacement for certified range safety." disclaimer renders wherever a verdict appears
- [ ] TXXX [P] Confirm the persistent disclaimer and hedging wording; remove any certification claim
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests MUST be written and MUST FAIL before implementation
- Models before services
- Services before endpoints
- Regenerate `packages/contract` after any API change, BEFORE the web task that consumes it
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Pytest contract test for [endpoint] in apps/api/tests/contract/test_[name].py"
Task: "Pytest unit test for [agent tool] incl. passing + failing fixture images in apps/api/tests/fixtures/images/"
Task: "Vitest + RTL test for [component] in apps/web/tests/test_[name].test.tsx"
Task: "Playwright e2e for this story's demo scenario in e2e/[scenario].spec.ts"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in apps/api/db/models/[entity1].py"
Task: "Create [Entity2] model in apps/api/db/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group, Conventional Commits format
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- A task is only done when every condition in Constitution section 7 (Definition of Done) holds:
  compiles with no type errors, lint passes, its tests pass, it is visible in the UI if
  user-facing, and it matches the `spec.md` acceptance criteria
- If a task would violate a MUST in the constitution, stop and resolve it — record the
  deviation in `plan.md` Complexity Tracking, or amend the constitution explicitly via
  `/sp.constitution`
