# Persistent beta safeguards

Build quota history persists on the Railway job volume; restart recovery checks active durable jobs.
Hourly/daily limits and cooldown still use existing configuration. One active job per user is enforced
by the durable queue's unique index. Legacy synchronous routes remain process-local for active execution.

`GENESYS_DAILY_MODEL_TOKEN_BUDGET` defaults to 2,000,000 reserved estimated tokens globally per UTC day.
Each provider call reserves a conservative input/output/retry allowance before contacting the provider.
Reservations are not refunded. This is conservative usage accounting, not exact billed tokens or a dollar
spending cap. Set a separate provider-account spending limit for invoice protection.
Reaching the allowance stops new model work while retaining files; it can also interrupt an active build.

Compiler warnings predicting assignment-to-constant runtime throws now fail verification and enter repair.
Browser checks exercise recognized game start/canvas/restart controls and recheck runtime errors afterward.
Existing synthetic book checks remain. This does not verify every game mechanic or booking workflow.
Reports submitted through the existing Report a problem UI are stored durably with authenticated user,
project, request reference and timestamp, in addition to operational logs. No new public report-reading API exists.

Compilation checked. Remaining beta gates: live cross-account isolation checks, booking workflows,
parallel fresh-project completion and a complete forced-restart recovery run. No new live scenario tests
were run for this change. Keep the first beta invite-only and small until those gates pass.
