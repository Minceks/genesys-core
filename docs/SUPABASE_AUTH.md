# Supabase backend integration

Set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` on Railway. With either
variable set, protected endpoints require a validated user bearer token;
shared API keys cannot bypass these checks. Missing configuration fails closed.
With neither variable set, existing builder routes retain legacy API key access.

Send `Authorization: Bearer <user-access-token>`. The backend validates identity
through `/auth/v1/user` and queries project ownership with the user's token,
preserving database RLS. It does not use the Supabase secret key.

Create the projects table and ownership RLS policies before deployment.
`POST /api/projects` accepts `{ "name": "Untitled project" }` and returns the
created project with status 201. `GET /api/projects/<uuid>` returns an owned
project. Missing projects and other users' projects both return 404.

File, build, job, preview and feedback requests must reference an owned UUID.
Promotion also requires a valid checkpoint proof and an administrator user UUID
in `GENESYS_PROMOTION_ADMIN_IDS` (comma-separated). This limits review PR creation
against the shared production repository. No PR is automatically merged.

Deploy the frontend bearer-token changes together with the backend. Existing
browser-local beta projects are not automatically assigned to a signed-in user.
Validate cross-account denial, expired sessions and successful owner access
before opening public beta access.
