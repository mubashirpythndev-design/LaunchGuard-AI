# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

<!--
  LaunchGuard AI defaults fixed by the Constitution — copy these unless a Complexity Tracking
  entry justifies a deviation:

    Language/Version:      TypeScript 5 (strict) + Python 3.11
    Primary Dependencies:  Next.js (App Router), FastAPI, OpenCV, YOLOv8
    Storage:               SQLite via SQLAlchemy (swappable)
    Testing:               Vitest + RTL, Playwright, Pytest
    Project Type:          web (two deployables — see Structure Decision)

  Performance Goals and Constraints remain unspecified by the constitution. For this product they
  MUST be measurable and stated here, e.g. time from upload to streamed verdict, and the maximum
  frame interval for the live monitor. Treat an unstated value as NEEDS CLARIFICATION.
-->


## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md`. Every MUST below is blocking; a violation must be
resolved by changing the plan, or justified in Complexity Tracking — never by reinterpreting the
principle.*

- [ ] **S1 Deterministic verdict** — Is the GO / HOLD / NO-GO verdict produced by a rule
  engine over structured findings, with the LLM limited to explaining, recommending, and
  escalating? (Constitution 2.I)
- [ ] **S2 Fail safe** — Does every error, timeout, and low-confidence path yield
  `severity: "warning"`, and do missing mandatory checklist inputs yield `HOLD`? (2.II)
- [ ] **S3 Explainable** — Does every finding carry module, check id, severity, message,
  confidence, metrics, and an overlay when visual? (2.III)
- [ ] **S4 Honest uncertainty** — Is user-facing copy hedged, is the "Decision-support tool.
  Not a replacement for certified range safety." disclaimer present wherever a verdict renders,
  and is no certification claim made? (2.IV)
- [ ] **S5 Vision proposes** — Does the agent only orchestrate CV tools, with every number
  traceable to a tool result? (2.V)
- [ ] **A1 Two deployables, one contract** — Are the only two deployables `apps/web` and
  `apps/api`, with `packages/contract` generated from OpenAPI and no hand-written frontend
  types? (3.I)
- [ ] **A2 CV in Python only** — Is all CV in `apps/api`, with the browser limited to
  capture, upload, and render? (3.II)
- [ ] **A3 Pure tools, streaming, persistence** — Are agent tools pure
  `(input) -> Finding` functions, is progress streamed over SSE, and is state in SQLite via
  SQLAlchemy? (3.III–3.V)
- [ ] **F1 Frontend discipline** — `strict: true`, no `any`, shadcn/ui primitives, React Bits
  off the decision path, Tailwind + shadcn theme, TanStack Query, React Hook Form + Zod, WCAG
  AA, non-colour-only signals, `prefers-reduced-motion`, Server Components by default. (4.I–4.VII)
- [ ] **Q1 Quality bar** — Are ESLint + Prettier (web) and Ruff + mypy (api) configured, are
  Vitest/RTL, Playwright, and Pytest fixture tests planned, does every CV module get a passing
  and a failing fixture, is `.env.example` maintained, and is `OPENAI_API_KEY` server-side only?
  (5.I–5.IV)
- [ ] **S6 Scope** — Is the plan limited to the 3 modes and 3 demo scenarios, with thermal,
  drone, telemetry, and digital twin explicitly deferred? (6.I–6.III)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: The layout below is MANDATED by Constitution 3.I (Two Deployables, One
  Contract) and MUST NOT be replaced with a single-project, generic frontend/backend, or mobile
  layout. Expand the tree with the real paths for this feature, but keep the three top-level
  directories. The delivered plan must not include Option labels.
-->

```text
apps/
├── web/                      # Next.js (App Router) + TypeScript strict
│   ├── app/                  # App Router routes and layouts
│   ├── components/
│   │   ├── ui/               # shadcn/ui primitives (CLI-managed)
│   │   └── react-bits/       # React Bits (shadcn registry) — atmosphere only
│   ├── lib/                  # TanStack Query, RHF + Zod wiring
│   ├── stores/               # Zustand — live-monitor store only
│   └── tests/                # Vitest + React Testing Library
├── api/                      # Python 3.11 + FastAPI
│   ├── app/                  # FastAPI app, routers, SSE endpoints
│   ├── agent/                # Orchestrator + pure (input) -> Finding tools
│   ├── cv/                   # OpenCV + YOLOv8 modules (pure functions)
│   ├── rule_engine/          # Deterministic GO / HOLD / NO-GO
│   ├── db/                   # SQLAlchemy models (SQLite)
│   └── tests/
│       ├── fixtures/images/  # Passing + failing images per CV module
│       ├── unit/             # Pytest for tools and rule engine
│       └── contract/         # OpenAPI conformance
└── contract/                 # packages/contract — generated TS types + Zod schemas
    ├── openapi.json          # Source of truth: generated from apps/api
    ├── src/                  # types.ts, schemas/*.ts — generated, never hand-edited
    └── scripts/              # Generation command

e2e/                          # Playwright — one spec per demo scenario (GO, HOLD, NO-GO)
```

**Structure Decision**: Record which feature areas land in each deployable and confirm the
contract is generated from `apps/api` rather than authored. If this plan adds a directory
outside the three above, justify it in Complexity Tracking.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
