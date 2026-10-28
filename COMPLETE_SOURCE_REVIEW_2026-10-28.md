# Complete source review and bounded verification recovery ? 2026-10-28

Latest new-game request 06f0fd3e71cb4442b5c44c1f6ec54253 fell back after its draft reviewer reported receiving no source, then passed three browser workflows before repair planning timed out twice.

Oversized source review requests now preserve complete draft files, existing modules and shared interfaces as valid JSON. Only optional design fields are removed to fit the configured token budget. If complete source still cannot fit, review stops before model transport and DraftReviewFailed retains the full draft for ordinary coordinator recovery. Empty drafts are rejected before review. Normal unrelated conversation compaction remains unchanged.

Browser repair planning gets one bounded 90-second timeout attempt instead of repeating two 45-second attempts; the parent request deadline and 30-second browser execution reserve still apply. Initial planning retains its 60-second limit. Existing coverage/evidence retention remains enforced.

Validation: 175 tests passed against isolated release source. A live configured-model synthetic review passed with all three counter modules under a 4000-token input cap after oversized optional design notes were compacted. No private project source was sent to a model.

A separate local audit of the actual generated game identified canvas-before-mount startup, HUD field mismatch and competing simulation-loop defects. Its source and audit evidence are retained in workspace evidence; runtime repairs are validated separately from the platform release.
