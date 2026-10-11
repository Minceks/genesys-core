# Two-worker new-project builds

Enable `GENESYS_PARALLEL_BUILD=true` on the backend.
Only untouched independent React starters are eligible; edits and restart recovery retain the single-agent flow.
The coordinator creates a shared logic interface once. OpenAI drafts App.jsx and styles.css while Gemini
simultaneously drafts projectLogic.js. Workers return draft source in memory and cannot write to the sandbox.
The coordinator validates file ownership, writes drafts sequentially, and runs existing build/browser checks.
Verification failures use the existing bounded repair flow. Draft failures fall back to ordinary implementation.
Durable jobs preserve accepted requests and applied files; interrupted in-memory drafts are regenerated.

Log `parallel_drafts_ready` records drafting duration. Speed improvements remain unmeasured and are not guaranteed:
planning, provider latency and repairs can outweigh concurrency. Parallel drafting incurs additional model calls.
Compilation was checked; an end-to-end parallel build has not yet been performed.
