# Deviations & Technical Decisions Log

This document records deliberate, justified deviations from initial drafts and outline defaults, in compliance with `.specify/memory/constitution.md`.

## Phase 0: Setup & Bootstrap (T001-T013)

1. **Target Python Version Alignment (`pyproject.toml`)**:
   - *Deviation*: Updated `python_version` in `apps/api/pyproject.toml` from `3.11` to `3.12` (with `>=3.11` compatibility).
   - *Rationale*: The local machine environment is Python `3.12.8`. Modern numpy type stubs (`numpy/__init__.pyi:737`) require Python 3.12 syntax parsing to avoid mypy syntax errors.
   - *Impact*: Zero regression; full forward compatibility.

2. **Package Name Alignment**:
   - *Deviation*: Named web package `@launchguard/web` in `apps/web/package.json`.
   - *Rationale*: Matches the monorepo filter convention specified in `plan.md` and `quickstart.md` (`pnpm --filter @launchguard/web dev`).

3. **Vitest PostCSS Isolation**:
   - *Deviation*: Added `css: { postcss: { plugins: [] } }` to `apps/web/vitest.config.ts`.
   - *Rationale*: Prevents Vitest runner from attempting to execute Tailwind v4 PostCSS plugins in Node test environment, allowing `design-lint.test.ts` to execute rapidly and reliably.

## Phase 1: Foundational (T014-T051)

1. **SQLAlchemy Asyncio Greenlet Dependency**:
   - *Deviation*: Added `greenlet>=3.0.0` (and `sqlalchemy[asyncio]>=2.0.30`) to `apps/api/pyproject.toml`.
   - *Rationale*: SQLAlchemy 2's asyncio engine requires `greenlet` to run coroutines in asyncio tasks.
   - *Impact*: Zero regression; clean async SQLite execution.

2. **OpenAPI Export Virtual Environment Auto-Detection**:
   - *Deviation*: Enhanced `scripts/export_openapi.py` to auto-detect `apps/api/.venv` site-packages.
   - *Rationale*: Allows `pnpm generate` to be run seamlessly from the workspace root by any developer without requiring global pip installs or prior virtual environment activation.

3. **Web Testing Environment (`vitest.config.ts`)**:
   - *Deviation*: Installed `@testing-library/react` and `jsdom` in `apps/web` and set `environment: "jsdom"` in `apps/web/vitest.config.ts`.
   - *Rationale*: Required to execute component unit tests (`verdict.test.tsx` and `motion-safe.test.tsx`) in Vitest.

4. **Contract Subpath Exports**:
   - *Deviation*: Added `./types` and `./zod` subpath exports in `packages/contract/package.json`.
   - *Rationale*: Allows direct type-safe imports in `apps/web/lib/schemas.ts` while keeping `packages/contract/src/` completely generated and untouched by human hands.

