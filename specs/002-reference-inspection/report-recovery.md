# Completed-run report loading correction

The single-image upload route previously persisted the run, findings and annotated
image but omitted the report row. History links opened `/report/{run_id}`, while
`GET /api/runs/{run_id}/report` returned 404. The page ignored non-success responses
and could leave a loading or narrative-pending state indefinitely.

## Correction

- New single-image uploads persist a deterministic report before publishing completion.
  This route does not schedule an LLM call, so narrative status is explicitly unavailable.
- Missing reports for completed runs with stored verdict/risk can be recovered from
  persisted findings, checklist records and completion reasons. Recovery never reruns
  CV, the LLM or current rules, and never modifies the original verdict, risk or findings.
- Recovery is insert-only with conflict handling on run ID, preserving existing reports
  and making repeated/concurrent recovery requests safe. GET and share requests use it.
- Unknown, failed and unfinished runs do not receive invented reports.
- The report page uses TanStack Query, distinguishes an unfinished run from a missing
  report, stops polling on errors, displays an actionable retry, and closes its stream
  when the report no longer needs live narrative updates. The disclaimer stays visible.

## Verification

- 133 backend tests passed, including new report creation, historical NO-GO/risk
  preservation, idempotent recovery, sharing, and missing/unfinished cases.
- 61 frontend tests passed, including failed-load, retry, and historical/structured
  reason compatibility regressions. The single-image view normalizes both event
  formats to text rather than attempting to render reason objects.
- Strict mypy, Ruff, frontend typing/lint, and production build passed.
- A browser regression opens a single-image report from Recent range operations,
  verifies no perpetual progress/narrative loader, then reloads the report.
- All 12 browser scenarios passed against the production build. The reported
  historical run was recovered and its report endpoint verified to return HTTP 200,
  preserving its original HOLD verdict and risk score of 47.

Decision-support tool. Not a replacement for certified range safety.
