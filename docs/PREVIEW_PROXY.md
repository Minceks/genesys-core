# Preview service deployment

This service is separate from the GeneSys Flask API and main website. It is not
enabled in production yet. It forwards expiring Daytona signed URLs through
individual random hostnames so projects do not share browser origins.

## Domain and service

Prefer a separate registered domain dedicated to generated applications.
Use a wildcard such as `*.your-preview-domain.example` and keep GeneSys accounts
and cookies off that domain. Configure a separate Railway service with repository
root directory `/preview_proxy`; the Dockerfile runs the asynchronous HTTP and
WebSocket proxy. Configure Railway health checks at `/health`, one replica only.

Set `GENESYS_PREVIEW_DOMAIN` to the suffix without `*.` or a scheme. Set
`GENESYS_PREVIEW_PROXY_KEY` to an independent random secret of at least 32 characters.
Never expose this key to the frontend or generated apps.

Add Railway's wildcard DNS records including its verification TXT and certificate
challenge CNAME. Exact record values are supplied by Railway after domain creation.
Do not redirect preview traffic to Daytona in the browser: the service must
forward the content and WebSockets itself.

## Backend integration to activate after DNS is ready

After checking Supabase project ownership and starting the preview, the backend
registers the resulting signed Daytona URL using `POST /internal/previews` with
`X-GeneSys-Proxy-Key`. The returned URL goes to the frontend iframe. Browser
verification inside Railway can continue using the direct Daytona URL.

Links expire after 3500 seconds. Registry state is process-local: service restarts
invalidate existing links and users reconnect from the builder. Links are bearer
capabilities: anyone given a link can view that preview until expiry. The control
endpoint is server-authenticated; user session tokens are never forwarded to apps.

Only HTTPS signed Daytona URLs on application port 4173 are accepted. Internal
Daytona ports and arbitrary remote URLs cannot be registered. HTTP response
cookies are intentionally not forwarded in this initial version; generated apps
that require cookie login need an additional cookie-isolation implementation.
This initial service must be validated for HTTP, assets, WebSockets, expiration,
cross-project origins and upstream failures before activation.

Hosting under GeneSys changes the browser-facing domain; it does not guarantee
acceptance by Bite's security filter. Validate from the affected network.
