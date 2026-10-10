"""Separate preview service. Each expiring link receives its own origin."""
import asyncio
import hmac
import hashlib
import os
import re
import secrets
import time
from urllib.parse import urlsplit

import aiohttp
from aiohttp import web

HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
       'te', 'trailer', 'transfer-encoding', 'upgrade'}


def create_app():
    domain = os.environ['GENESYS_PREVIEW_DOMAIN'].strip().lower()
    secret = os.environ['GENESYS_PREVIEW_PROXY_KEY']
    if len(secret) < 32 or not re.fullmatch(r'[a-z0-9.-]+', domain):
        raise RuntimeError('A preview domain and a strong proxy key are required.')
    app = web.Application(client_max_size=10 * 1024 * 1024)
    entries = {}

    async def lifecycle(app):
        app['client'] = aiohttp.ClientSession(auto_decompress=False,
            cookie_jar=aiohttp.DummyCookieJar(),
            timeout=aiohttp.ClientTimeout(total=None, connect=10, sock_read=60))
        yield
        await app['client'].close()
    app.cleanup_ctx.append(lifecycle)

    async def register(request):
        supplied = request.headers.get('X-GeneSys-Proxy-Key', '')
        if not hmac.compare_digest(supplied.encode(), secret.encode()):
            raise web.HTTPUnauthorized()
        try:
            data = await request.json()
            upstream = urlsplit(data['url'])
            # Fixed application port and trusted Daytona domains only. No arbitrary proxy targets.
            host = upstream.hostname or ''
            allowed = re.fullmatch(r'417[34]-[a-zA-Z0-9-]+\.(?:daytonaproxy\d+\.eu|proxy\.daytona\.work)', host)
            if upstream.scheme != 'https' or not allowed or upstream.port or upstream.username or upstream.password or upstream.path not in ('', '/') or upstream.query or upstream.fragment:
                raise ValueError('Invalid upstream')
        except (ValueError, KeyError, TypeError):
            raise web.HTTPBadRequest(text='A signed Daytona application preview URL is required.')
        now = time.monotonic()
        for key in list(entries):
            if entries[key]['expires'] <= now:
                del entries[key]
        project_id = str(data.get('projectId') or '')
        if len(project_id) > 128:
            raise web.HTTPBadRequest(text='Invalid project identifier.')
        ticket = hmac.new(secret.encode(), ('project:' + project_id).encode(), hashlib.sha256).hexdigest()[:32] if project_id else secrets.token_hex(16)
        if ticket not in entries and len(entries) >= 256:
            raise web.HTTPServiceUnavailable(text='Preview capacity reached.')
        entries[ticket] = {'upstream': f'https://{host}', 'expires': now + 3500}
        return web.json_response({'url': f'https://{ticket}.{domain}/', 'expiresInSeconds': 3500})

    def headers(request):
        connection_headers = {x.strip().lower() for x in request.headers.get('Connection', '').split(',')}
        blocked = HOP | connection_headers | {'host', 'authorization', 'x-api-key', 'x-genesys-proxy-key', 'forwarded', 'x-forwarded-host', 'x-forwarded-for', 'x-forwarded-proto'}
        result = {k: v for k, v in request.headers.items() if k.lower() not in blocked and not k.lower().startswith('x-daytona-')}
        result['X-Daytona-Skip-Preview-Warning'] = 'true'
        return result

    async def proxy(request):
        host = request.host.split(':', 1)[0].lower()
        suffix = '.' + domain
        ticket = host[:-len(suffix)] if host.endswith(suffix) else ''
        entry = entries.get(ticket)
        if not entry or entry['expires'] <= time.monotonic():
            return web.Response(status=410, content_type='text/html', text='<h1>Preview unavailable</h1><p>Return to GeneSys and choose Reconnect to request a fresh preview.</p>', headers={'Cache-Control': 'no-store'})
        target = entry['upstream'] + request.raw_path
        upstream_headers = headers(request)
        try:
            if request.headers.get('Upgrade', '').lower() == 'websocket':
                protocols = [x.strip() for x in request.headers.get('Sec-WebSocket-Protocol', '').split(',') if x.strip()]
                for key in list(upstream_headers):
                    if key.lower().startswith('sec-websocket-'):
                        del upstream_headers[key]
                async with app['client'].ws_connect(target, headers=upstream_headers, protocols=protocols, max_msg_size=10 * 1024 * 1024) as upstream:
                    downstream = web.WebSocketResponse(protocols=[upstream.protocol] if upstream.protocol else (), max_msg_size=10 * 1024 * 1024)
                    await downstream.prepare(request)
                    async def relay(source, destination):
                        async for message in source:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                await destination.send_str(message.data)
                            elif message.type == aiohttp.WSMsgType.BINARY:
                                await destination.send_bytes(message.data)
                        await destination.close()
                    tasks = [asyncio.create_task(relay(upstream, downstream)), asyncio.create_task(relay(downstream, upstream))]
                    try:
                        await asyncio.wait(tasks, timeout=max(0, entry['expires'] - time.monotonic()), return_when=asyncio.FIRST_COMPLETED)
                    finally:
                        for task in tasks:
                            task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                    return downstream
            body = await request.read()
            async with app['client'].request(request.method, target, headers=upstream_headers, data=body, allow_redirects=False) as upstream:
                connection_headers = {x.strip().lower() for x in upstream.headers.get('Connection', '').split(',')}
                result_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP | connection_headers | {'set-cookie', 'access-control-allow-origin', 'access-control-allow-credentials'}}
                location = result_headers.get('Location')
                if location and location.startswith(entry['upstream'] + '/'):
                    result_headers['Location'] = 'https://' + host + location[len(entry['upstream']):]
                result_headers['Referrer-Policy'] = 'no-referrer'
                result_headers['Cache-Control'] = 'no-store'
                result_headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
                response = web.StreamResponse(status=upstream.status, headers=result_headers)
                await response.prepare(request)
                async for chunk in upstream.content.iter_chunked(65536):
                    await response.write(chunk)
                await response.write_eof()
                return response
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return web.Response(status=503, text='Preview is temporarily offline. Reconnect from GeneSys.', headers={'Cache-Control': 'no-store'})

    app.router.add_get('/health', lambda request: web.json_response({'status': 'ok'}))
    app.router.add_post('/internal/previews', register)
    app.router.add_route('*', '/{path:.*}', proxy)
    return app


if __name__ == '__main__':
    # Do not log capability URLs or signed upstream addresses.
    web.run_app(create_app(), host='0.0.0.0', port=int(os.getenv('PORT', '8080')), access_log=None)
