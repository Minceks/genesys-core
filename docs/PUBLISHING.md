# Beta publishing

POST `/publish` accepts projectId, checkpointId and promotionToken with the
signed-in owner's bearer token. A current signed build/browser verification
proof must match the saved verified snapshot. Publishing exports static build
files onto Railway's persistent volume, independently of Daytona.

Publishing is disabled by default. Set `GENESYS_PUBLISH_TEST_USER_IDS` to a
comma-separated list of Supabase user IDs for controlled test publications.
Only after acceptance checks, set `GENESYS_PUBLISH_ENABLED=true`.

Published links are public. New publications use an isolated `app-<id>` origin
under the configured preview domain. Republishing a project atomically switches
its active version while retaining the same link and older hashed assets.
Unpublish disables that link; republishing re-enables it. Credentials stay on
the backend. This first stage supports static apps using
Vite hashed assets; arbitrary root-relative links and client-side routers
need publication-aware base paths before they can be supported. PWA installation,
custom domains, database provisioning and app customer authentication are
not included. A booking demo is not a production booking service.

Before enabling beta: check asset loading and mobile access, stop Daytona,
restart Railway, confirm the link survives, verify ownership denial with a
second account, and check quota/storage behavior. Publications currently need
manual volume cleanup for retained revisions; do not enable unlimited public publishing.
