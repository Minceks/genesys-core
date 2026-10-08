# GeneSys API

## Overview

The GeneSys Cloud Agent exposes these HTTP routes:

- Health information
- Agent execution
- Project file listing
- File reading
- File writing
- Verified checkpoint promotion to a GitHub pull request

Routes use simple paths such as `/health`, `/agent/run`, and `/promote`.

The API returns JSON responses.

---

## Authentication

`GET /health` is public. All other endpoints require the `X-API-Key` HTTP
header. The server compares this value with `GENESYS_API_KEY`; if the server
key is unset, protected requests fail closed with `503`.

Example:

```http
X-API-Key: your-genesys-api-key
```

For the browser app, set `VITE_CLOUD_AGENT_API_KEY` to the same value during
the frontend build. Vite embeds `VITE_` variables in public JavaScript, so this
shared key is visible to visitors. Use it only for a trusted or private
prototype. For a public app, replace it with per-user authentication (for
example, validate Supabase access tokens on the server).

## Verified production promotion

`POST /promote` accepts the project ID and checkpoint ID returned by a
successful agent run, along with its short-lived promotion token:

```json
{
  "projectId": "genesys-project",
  "checkpointId": "genesys-checkpoint-1234567890",
  "promotionToken": "<short-lived token returned by /agent/run>"
}
```

The endpoint exports the referenced checkpoint from its Daytona sandbox. The
checkpoint is created after the orchestrator's required build and browser
verification succeed. The Cloud Agent publishes the snapshot to a dedicated
branch and opens a GitHub pull request; it never merges or deploys the change.
Production must still be reviewed and merged through the normal GitHub/Vercel
workflow. If the configured base branch moved after verification, promotion
returns `STALE_CHECKPOINT` and the request must be built and verified again.

Configure `GENESYS_GITHUB_TOKEN`, `GENESYS_GITHUB_REPOSITORY` (OWNER/REPO),
`GENESYS_GITHUB_BASE_BRANCH`, and `GENESYS_PROMOTION_SIGNING_KEY` in the Cloud
Agent environment. The signing key must be a separate random secret. Use a
fine-grained token limited to this repository with Contents read/write and
Pull requests read/write permissions. The token stays in the Cloud Agent and
is never passed to the Daytona sandbox.
