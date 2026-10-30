# Builder benchmark suite

Run from the repository with the project's Python environment:

```powershell
..\venv\Scripts\python.exe benchmarks/run.py
```

The reference store, illustrator portfolio, appointment form and task dashboard
validate the harness and local workflow recipes. They are hand-written reference
fixtures, **not evidence of AI generation quality or speed**. Both desktop and phone
checks retain screenshots, runtime errors, layout findings, passed behaviors and
load/check durations in JSON and Markdown. No model calls, payments or network
writes occur during the benchmark.

To compare generated applications, copy `reference.json`, set each case's `path`
to its built entry page (or `url` to a reviewed preview), and provide its original
request, requirements contract, source paths and reviewed verification plan. A
matching supported recipe needs no plan. Unknown apps require a reviewed plan;
the runner never invents a passing result. Remote URLs require `--allow-remote`.
Use only isolated test apps and synthetic data. Reference selectors must be adapted
to the generated app's real accessible names.

Include the builder job's `metrics` as `buildMetrics` to compare execution time,
provider-reported responses/tokens, repair attempts and file counts. Browser load
time is separate from build time. A benchmark must retain the same prompts,
requirements and viewports across revisions; changed expectations are a new baseline.
Fresh paid generation benchmarks require explicit approval for the external model
calls and any project source transmitted; this offline runner does not do them.

For explicitly authorized fresh tests, use a new evidence directory:

```powershell
..\venv\Scripts\python.exe -m benchmarks.fresh --execute --max-usd 5 --output .verification-evidence/fresh-builds-NEW
..\venv\Scripts\python.exe -m benchmarks.review_fresh .verification-evidence/fresh-builds-NEW
```

This runs four fixed synthetic requests through the actual orchestrator on pinned
`gpt-5-mini`, with a $4 persistent model reservation ceiling and $1 reserved for
temporary Linux sandboxes. All provider fallbacks use the guarded model. Each call
reserves the full model context plus its bounded output before execution; failures
with unknown usage retain that reservation. SDK retries are disabled. Workers run
sequentially, with isolated local state and new project UUIDs. Sandboxes have a
20-minute TTL, a resource bound, and are deleted after public source/dist export.
Cleanup must succeed before the next worker. Model usage is a conservative upper
estimate, not an invoice. Public pricing: [OpenAI](https://developers.openai.com/api/docs/models/gpt-5-mini),
[Daytona](https://www.daytona.io/pricing). Do not run concurrent controllers against
the same ledger. The pinned-model results do not establish performance of the
production default/fallback provider combination.

Raw logs and source artifacts stay in ignored `fresh-builds*` evidence directories.
The offline presentation review captures desktop/phone screenshots and runtime/
layout findings; the full pipeline's result records behavior verification. Neither
objective layout checks nor a screenshot alone establish subjective design quality.

For the reviewed booking/dashboard artifacts from the first fresh suite, run
`python -m benchmarks.review_workflows .verification-evidence/fresh-builds-20261018-a`.
It tests actual keyboard entry, validation, persistence and cancellation/deletion
using newly created synthetic records only. It exits nonzero if a case fails;
the original booking artifact fails real typing even though programmatic filling
lets its remaining workflows be examined. Its selectors are specific to those
reviewed synthetic artifacts, not general verification recipes.

Use `--presentation-regression` to repeat the same behavior assertions after a
CSS-only edit, on both viewports. The edit changes heading spacing, page padding
and control radii, and is reapplied after reload. Requests, handlers, storage keys
and acceptance criteria stay the same. This produces 16 runs for the four reference
apps. Reports label baseline versus presentation-edit; these runs demonstrate
regression protection, not fresh AI generation or subjective visual quality.
