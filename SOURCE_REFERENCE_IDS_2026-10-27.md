# Server-owned source evidence references ? 2026-10-27

Railway request 399b8151ad524d7ebc768a91ca826ae4 failed specification planning after rejecting an invented Save Progress control, a null browser citation and a source excerpt that did not exactly match supplied code.

Policy 7 supplies a bounded catalog of overlapping source windows. The model selects a referenceId from the schema's exact enum; the server resolves it to the original path and excerpt before validation and persistence. The browser requirement schema requires a non-null reference object, while visual/external requirements use null. Unknown IDs still fail. Models no longer need to transcribe source code. Existing controls/capability checks remain in place.

The catalog replaces duplicate full-source fields in planner context. Each window is at most 1000 characters with 200-character overlap, preserving the existing 48000-character source-reading budget. Resolved evidence still passes the existing exact-source validation. Older cached policies regenerate.

A real configured-model test using only a synthetic counter returned three browser requirements with valid server-resolved evidence. CRLF and Unicode remained byte-for-character intact in stored excerpts. No private project source or real user request was included in this test. Full user-game generation has not been rerun.
