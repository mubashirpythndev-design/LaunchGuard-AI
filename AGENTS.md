# hackathon KYS Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-09-29

## Active Technologies

- TypeScript 5 (`strict: true`, no `any`) + Python 3.11 + Next.js 15 (App Router, Turbopack), React 19, Tailwind CSS v4, shadcn/ui, (001-launchguard-mvp)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

TypeScript 5 (`strict: true`, no `any`) + Python 3.11: Follow standard conventions

## Recent Changes

- 001-launchguard-mvp: Added TypeScript 5 (`strict: true`, no `any`) + Python 3.11 + Next.js 15 (App Router, Turbopack), React 19, Tailwind CSS v4, shadcn/ui,

<!-- MANUAL ADDITIONS START -->

## Governing Document

`.specify/memory/constitution.md` (v1.0.0) is non-negotiable and supersedes every other practice,
default, and template in this repository. Read it before writing code. It overrides the generated
"Project Structure" and "Commands" blocks below, which the generator infers from a generic web
template and cannot know to be wrong for this project (tracked as `TODO(TOOLING_LAYOUT)` in the
constitution's Sync Impact Report).

## Real Project Structure

```text
apps/web/          Next.js 15 App Router + TypeScript strict
apps/api/          FastAPI, CV, agent, rule engine, SQLite
packages/contract/   generated types + Zod schemas (src/ is git-ignored)
e2e/               Playwright — one spec per demo scenario
scripts/           openapi export, dev orchestration, fixture seeding
```

There is no `backend/`, `frontend/`, or `src/` directory.

## Real Commands

```bash
pnpm install && pnpm generate          # generate = export OpenAPI, then build packages/contract
uvicorn app.main:app --reload --port 8000 --workers 1   # from apps/api; --workers 1 is REQUIRED
pnpm --filter @launchguard/web dev

pnpm --filter @launchguard/web typecheck
pnpm --filter @launchguard/web lint
cd apps/api && mypy --strict app cv agent rule_engine db && ruff check .
pytest                                     # from apps/api
pnpm --filter @launchguard/web test
pnpm exec playwright test
```

## Non-Negotiables Worth Restating

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
- The disclaimer "Decision-support tool. Not a replacement for certified range safety." is
  visible on all five screens.

## Current Feature

`specs/001-launchguard-mvp/` — `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/api.md`, `contracts/events.md`, `quickstart.md`. `tasks.md` is produced by `/sp.tasks`.

<!-- MANUAL ADDITIONS END -->
