# Quickstart: LaunchGuard AI MVP

**Feature**: `001-launchguard-mvp` | **Date**: 2026-09-29
**Plan**: [plan.md](./plan.md)

> This describes the **target** developer setup that `/sp.tasks` will produce. No application code
> exists yet; the commands below are the contract the tasks must satisfy, not instructions that
> work today.

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node | 22+ | `node --version` |
| pnpm | 9+ | `pnpm --version` |
| Git | any | `git --version` |

No database server, no Docker, no cloud account, and no API key are required. SQLite is a file.
The narrative model is optional — the product is fully demonstrable without it (NFR-006).

## Layout

```text
apps/web/          Next.js 15 App Router + TypeScript strict
apps/api/          FastAPI, CV, agent, rule engine, SQLite
packages/contract/ generated types + Zod schemas (git-ignored src/)
e2e/               Playwright — one spec per demo scenario
scripts/           openapi export, dev orchestration, fixture seeding
specs/001-launchguard-mvp/   this feature's artifacts
.specify/memory/constitution.md   the governing document
```

There is no `launchguard/` wrapper directory and no `specs/constitution.md`. The constitution lives
at `.specify/memory/constitution.md` and the feature artifacts live under `specs/001-launchguard-mvp/`.

## First-time setup

```bash
git clone <repo> && cd "hackathon KYS"
git checkout 001-launchguard-mvp

pnpm install
pnpm generate          # export OpenAPI from apps/api, then generate packages/contract/src
```

`pnpm generate` is the two-step contract pipeline (R1):

```bash
python scripts/export_openapi.py       # app.openapi() -> packages/contract/openapi.json
npx @hey-api/openapi-ts                # -> packages/contract/src (types + Zod v4)
```

It is wired as a `prebuild` hook, so it also runs automatically before `pnpm build`. It is
**idempotent and offline** — it imports the FastAPI app rather than starting a server, so it never
depends on a running process or on request-time state.

Python dependencies install separately:

```bash
cd apps/api
python -m venv .venv && . .venv/Scripts/activate    # Windows
python -m pip install -r requirements.txt
```

Key pinned dependencies: `fastapi`, `pydantic>=2`, `uvicorn[standard]`, `opencv-python`,
`ultralytics`, `langgraph`, `langgraph-checkpoint-sqlite`, `aiosqlite`, `openai`, `sqlalchemy>=2`,
`python-multipart`. `ultralytics` downloads YOLOv8n weights on first run; the first launch of a
CV module is therefore slower than subsequent ones.

## Configuration

Copy the template. It is committed and must stay current (Constitution 5.III):

```bash
cp .env.example apps/api/.env
```

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | no | — | **Server-side only.** Never a `NEXT_PUBLIC_*` variable, never referenced from `apps/web`. CI greps for this. |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Swappable without code changes (spec Assumption 3). |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///./launchguard.db` | Swappable store (Constitution 3.V). |
| `CHECKPOINT_DB` | no | `./checkpoints.sqlite` | LangGraph `AsyncSqliteSaver` file. |
| `MEDIA_ROOT` | no | `./media` | Where run images are written, locally only. |
| `CORS_ORIGINS` | no | `http://localhost:3000` | Comma-separated. |
| `LOG_LEVEL` | no | `INFO` | |
| `OPENAI_TIMEOUT_S` | no | `6.0` | Hard narrative timeout. The verdict is never blocked by it. |

With no `.env` at all, the app starts, every mode works, and reports render on the template path
with `narrative.status = "unavailable"` (FR-026).

## Running

Two terminals, or `pnpm dev` to run both.

```bash
# terminal 1 — API on :8000
cd apps/api && uvicorn app.main:app --reload --port 8000 --workers 1

# terminal 2 — web on :3000
pnpm --filter @launchguard/web dev
```

> **`--workers 1` is required, not a default.** SSE fan-out uses an in-process `asyncio` pub/sub
> backed by the persisted `run_events` log (R5). A second worker would open a second pub/sub that
> knows nothing about events published by the first, so subscribers on the second worker would
> stall between heartbeats. A multi-worker deployment needs a broker; for a single-operator,
> single-machine MVP that trade is not worth it. If you must scale workers, put Redis pub/sub
> behind the same `run_events` log.

Open <http://localhost:3000>. The five screens are `/`, `/inspect`, `/monitor`, `/history`, and
`/report/[runId]`.

## Verifying the system end to end

```bash
# 1. Contract is current — regenerating must produce no diff
pnpm generate && git status --porcelain packages/contract

# 2. Types and lint
pnpm --filter @launchguard/web typecheck && pnpm --filter @launchguard/web lint
cd apps/api && mypy --strict app cv agent rule_engine db

# 3. Rule engine — no network, no model, no fixtures needed
pytest tests/unit/test_verdict.py tests/unit/test_risk.py tests/unit/test_config.py -q

# 4. CV against real fixture images
pytest tests/unit -q

# 5. Demo scenarios with the network disabled
pytest tests/e2e -q

# 6. Browser tests
pnpm --filter @launchguard/web test
pnpm exec playwright test
```

Steps 3 and 5 are the ones that matter most: the rule engine test proves a verdict is computed
without any model, and the offline demo test proves FR-035 and SC-008.

## The three demo scenarios

Available from **Load demo scenario** on the dashboard, or:

```bash
for k in normal misaligned_fin person_near_pad; do
  curl -sX POST localhost:8000/api/demo/scenarios/$k/run | jq -r .run_id
done
```

| Key | Expected verdict | Drives the verdict through |
|---|---|---|
| `normal` | `GO` | Every check `ok`. Risk score stays in the 0–30 band even at lower confidence. |
| `misaligned_fin` | `HOLD` | `fin.alignment` `warning` at 4.2° ± 1.5°, inside the ambiguity margin of the 3.0° threshold, so the report carries the not-distinguishable note. |
| `person_near_pad` | `NO-GO` | `zone.occupancy` `critical`. |

Each scenario's fixture image **is** the `__pass` or `__fail` member of the corresponding CV
module's fixture set (R14), so the asset shown to a judge is the asset CI verified. Demo runs
execute the real pipeline with complete bundled manual inputs, so they never pause and always reach
a verdict (FR-036, SC-001).

To rehearse the offline path, disconnect the network and load all three. Each must still complete
with its expected verdict and a template report (SC-008).

## Walkthrough for a judge

1. **Dashboard** — latest verdict, risk gauge, checklist, recent runs.
2. **Load demo scenario → Misaligned fin** — watch the agent timeline advance through all five
   steps as events stream in. Verdict badge settles on `HOLD`; the fin finding shows `4.2°` and
   the ambiguity note. Risk gauge lands in the 40–69 band.
3. **Load demo scenario → Person near pad** — `NO-GO`, gauge in the 70–100 band.
4. **Safety Report** — checklist pass/fail per step, reasons in priority order, recommended
   actions, `Verdict computed by rules; explanation by AI`, and the disclaimer.
5. **Share** — generate a link, open it in a private window: read-only report, no controls, no
   other runs.
6. **Launchpad Monitor** — draw a danger zone over a still image, then load the
   `person_near_pad` fixture: the banner switches to `DANGER` with text and an icon as well as
   colour, and the detection log records the transition.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| SSE never updates; heartbeat only | The API is running more than one worker. Restart with `--workers 1` (R5). |
| UI stuck on a spinner after upload | A proxy is buffering the stream. Confirm `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no` survive the Next.js proxy (R5). |
| `narrative.status` is `unavailable` | Expected without `OPENAI_API_KEY`, or the model timed out past `OPENAI_TIMEOUT_S`. The verdict is unaffected (FR-026). |
| Report shows an empty reasons list | `validate_finding()` rejected a finding. Check the API log for `InadmissibleFinding` — this is the Constitution 2.III guard firing, not a bug to bypass. |
| A CV module is slow on first call | YOLOv8n weights download and load once. Subsequent calls are cached by the lazy singleton (R10). |
| Fin angle is off by more than 1.5° | The MVP measures a projected angle in the image plane with no camera calibration (spec Assumption 1). Confirm the vehicle is side-on before treating it as a defect. |
| Zone does not re-render in the same place | The zone is stored normalized; verify `source_width`/`source_height` were captured on the run (FR-012). |
| `mypy` errors in `cv/` | Expected if a module returns a dict. Tools must return the `Finding` dataclass (Constitution 2.III). |
| Contract looks stale in the editor | `packages/contract/src/` is generated and git-ignored. Run `pnpm generate`; do not edit it. |

## Before opening a pull request

Every item is a merge gate (Constitution 5 and section 7), and failing any one means the change is
not done regardless of schedule pressure:

- [ ] `pnpm typecheck` and `pnpm lint` clean in `apps/web`
- [ ] `mypy --strict` clean and `ruff check` clean in `apps/api`
- [ ] `pytest` green, including every CV module's `__pass` **and** `__fail` fixture
- [ ] `vitest` and `playwright` green, with the three demo-scenario specs asserting their expected verdicts
- [ ] `pnpm generate` produces no diff
- [ ] No `any` in `apps/web`; any `@ts-ignore` carries a comment naming its reason
- [ ] `OPENAI_API_KEY` appears only in `apps/api` and in `.env.example`, never in a
      `NEXT_PUBLIC_*` variable or in `apps/web`
- [ ] The disclaimer is visible on all five screens
- [ ] No React Bits component on the verdict badge, finding list, severity indicators, or
      disclaimer
- [ ] Commit message follows Conventional Commits; one task, one commit
