# Request-driven functional verification

The browser verification phase now uses one shared declarative executor rather
than app-type branches. A model plans up to eight checks from the original
request, bounded source evidence and rendered accessible controls. Each check uses bounded browser actions
and must assert an outcome after its last action. No generated JavaScript runs.

Malformed plans and uncertain test failures remain verification failures. Failed
assertions receive a separate source/DOM diagnosis; only confirmed app defects
enter the existing repair loop. Completion payloads include passed
check names and unverified requirements, which the builder displays. Missing
controls must fail rather than silently skipping the requested behavior. Plans
declare requirement IDs and checks declare which IDs their outcomes cover.
Skipped or failed checks cannot contribute to coverage, and uncovered core
requirements block completion. This coverage is model-derived, not an independent
proof that every possible requirement was identified.

Retrying the same failed prompt reuses its successful build when its source and
build-output fingerprint still matches. Changed files use the normal build flow.
The retry intent persists in the durable job payload. Incomplete verification
preserves the current preview while keeping publishing gated.

Verification runs in the agent's isolated browser with synthetic records. Network
writes are blocked; server-backed flows need a dedicated test environment and are
reported as unverified. This does not prove exhaustive correctness, multi-user
behavior, payments or real external integrations. Plans can be imperfect; evaluate
them on fresh projects before expanding beta. Verification uses a bounded plan
call, at most one plan revision, and an additional diagnosis call when needed.
Browser worker calls preserve the request and usage-accounting context.

The older content_checks module remains for compatibility; the active browser
verification path uses functional_verification.py.
