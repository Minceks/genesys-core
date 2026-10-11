# Request-driven functional verification

The browser verification phase now uses one shared declarative executor rather
than app-type branches. A model plans up to eight checks from the original
request and rendered accessible controls. Each check uses bounded browser actions
and must assert an outcome after its last action. No generated JavaScript runs.

Failed checks enter the existing repair loop. Completion payloads include passed
check names and unverified requirements, which the builder displays. Missing
controls must fail rather than silently skipping the requested behavior.

Verification runs in the agent's isolated browser with synthetic records. Network
writes are blocked; server-backed flows need a dedicated test environment and are
reported as unverified. This does not prove exhaustive correctness, multi-user
behavior, payments or real external integrations. Plans can be imperfect; evaluate
them on fresh projects before expanding beta. Each verification pass adds one
bounded provider call and uses the existing model allowance.

The older content_checks module remains for compatibility; the active browser
verification path uses functional_verification.py.
