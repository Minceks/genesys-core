# Default build standard

Every implementation path now receives the same default: premium UI, useful functions and solid engineering within the user's requested scope. `BUILD_STANDARD` in `agent/design_quality.py` defines the three expectations and requires separate evidence for compilation, browser workflows and rendered design. It explicitly rejects static mockups substituted for apps, no-op actions and fabricated integration success.

The sequential agent receives this before its implementation instructions, including edit and recovery requests. The parallel planner, UI worker, logic worker and joint source reviewer each receive the same standard independently. Focused presentation edits also receive it with their existing patch-only scope restrictions. The saved product quality contract includes it so the design handoff and reviewer share the delivery expectations.

This does not broaden small fixes into unsolicited redesigns, trigger extra model calls on verification-only retries, change payment scope or turn missing visual evidence into approval. Existing build, browser and bounded screenshot-review checks remain separate. Premium is the requested delivery standard, not an automatic aesthetic certification.

Validation: 123 tests passed, including actual parallel planner/worker/reviewer payloads, focused-edit scope, all product-family contracts, contact-sheet capture, source/interface review, saved-build retry behavior, specification recovery and browser lifecycle. Python compilation checks passed for the four changed runtime modules. No paid AI generation was performed.

Deployment `88bc4216-8c6d-4862-b777-308e004ca447` is SUCCESS. The REA browser deployment fixture passed on its first attempt. Production health returned HTTP 200, and filtered startup logs showed normal worker startup without errors. Fresh generated-product comparisons remain necessary to judge consistency of actual model output.
