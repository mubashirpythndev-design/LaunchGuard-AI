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
