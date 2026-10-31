"""Isolated project origins for durable builds and temporary editor previews."""
import asyncio
import hmac
import hashlib
import os
import re
import secrets
import time
import logging
from urllib.parse import urlsplit

import aiohttp
from aiohttp import web
try:
    from .selection_bridge import inject
except ImportError:
    import importlib.util
    from pathlib import Path
    bridge_spec=importlib.util.spec_from_file_location('genesys_selection_bridge',Path(__file__).with_name('selection_bridge.py'))
    bridge_module=importlib.util.module_from_spec(bridge_spec)
    bridge_spec.loader.exec_module(bridge_module)
    inject=bridge_module.inject

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
        notification = asyncio.create_task(notify_deployment())
        yield
        notification.cancel()
        await asyncio.gather(notification, return_exceptions=True)
        await app['client'].close()
    app.cleanup_ctx.append(lifecycle)

    async def notify_deployment():
        key = os.getenv('GENESYS_DEPLOY_SMOKE_KEY', '')
        backend = os.getenv('GENESYS_SMOKE_BACKEND_URL', '').rstrip('/')
        if (not os.getenv('RAILWAY_ENVIRONMENT_ID') or os.getenv('GENESYS_DEPLOY_SMOKE_ENABLED', '1') == '0'
                or len(key) < 32 or not backend.startswith('https://')): return
        deployment = os.getenv('RAILWAY_DEPLOYMENT_ID', 'startup')
        own = os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
        # A wildcard DNS name is not a resolvable URL host. Probe a concrete
        # hostname on the same wildcard certificate and routing configuration.
        if own.startswith('*.'): own = 'deployment-check.' + own[2:]
        deadline = time.monotonic() + 180
        failure, stage = 'not_ready', 'rollout'
        for _ in range(60):
            if time.monotonic() >= deadline: break
            try:
                if own:
                    stage = 'rollout'
                    async with app['client'].get('https://' + own + '/health', allow_redirects=False,
                            timeout=aiohttp.ClientTimeout(total=8)) as response:
                        if response.status != 200 or (await response.json()).get('deploymentId') != deployment:
                            failure = 'http_' + str(response.status) + '_or_version_pending'
                            await asyncio.sleep(3); continue
                stage = 'notification'
                async with app['client'].post(backend + '/internal/deployment-smoke',
                        json={'source': 'preview-router', 'deploymentId': deployment},
                        headers={'X-GeneSys-Smoke-Key': key}, allow_redirects=False,
                        timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status == 202:
                        logging.getLogger(__name__).info('deployment_smoke_notified source=preview-router')
                        return
                    failure = 'http_' + str(response.status)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
                failure = type(error).__name__
            await asyncio.sleep(3)
        logging.getLogger(__name__).error('deployment_smoke_notification_failed source=preview-router stage=%s reason=%s', stage, failure)

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
        result['Accept-Encoding'] = 'gzip'
        return result

    async def proxy(request):
        host = request.host.split(':', 1)[0].lower()
        suffix = '.' + domain
        ticket = host[:-len(suffix)] if host.endswith(suffix) else ''
        if re.fullmatch(r'[0-9a-f]{32}', ticket):
            backend = os.getenv('GENESYS_PUBLISHED_BACKEND_URL', '').rstrip('/')
            if backend.startswith('https://'):
                if request.method not in {'GET', 'HEAD'}:
                    return web.Response(status=405)
                internal_headers = {'X-GeneSys-Proxy-Key': secret, 'Accept-Encoding': 'gzip'}
                for key in ('Accept', 'If-None-Match', 'If-Modified-Since', 'Range'):
                    if key in request.headers:
                        internal_headers[key] = request.headers[key]
                target = backend + '/internal/preview-builds/' + ticket + request.rel_url.raw_path
                try:
                    async with app['client'].request(request.method, target, headers=internal_headers, allow_redirects=False) as upstream:
                        # An absent durable project may still have a live editor.
                        # A missing asset in a hosted project must stay a 404.
                        if upstream.status != 404 or upstream.headers.get('X-GeneSys-Preview-Hosted') == '1':
                            result_headers = {k:v for k,v in upstream.headers.items() if k.lower() not in HOP | {
                                'set-cookie', 'content-security-policy', 'access-control-allow-origin', 'x-genesys-preview-hosted'}}
                            result_headers['Content-Security-Policy'] = 'sandbox allow-scripts allow-same-origin allow-forms allow-popups allow-downloads'
                            result_headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
                            result_headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(self)'
                            result_headers['Cache-Control'] = 'no-cache'
                            content=await upstream.read()
                            if upstream.status==200:content=inject(content,result_headers)
                            return web.Response(status=upstream.status, body=content, headers=result_headers)
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    return web.Response(status=503, text='Saved build temporarily unavailable. Please retry.', headers={'Cache-Control':'no-store'})
        if re.fullmatch(r'app-[0-9a-f]{32}', ticket):
            backend = os.getenv('GENESYS_PUBLISHED_BACKEND_URL', '').rstrip('/')
            if not backend.startswith('https://'):
                return web.Response(status=503, text='Published hosting is not configured.')
            publication = ticket[4:]
            prefix = '/apps/' + publication
            path = request.rel_url.raw_path
            if not path.startswith(prefix + '/'):
                path = prefix + path
            if request.method not in {'GET', 'HEAD'}:
                return web.Response(status=405)
            try:
                async with app['client'].request(request.method, backend + path, allow_redirects=False) as upstream:
                    result_headers = {k:v for k,v in upstream.headers.items() if k.lower() not in HOP | {'set-cookie','content-security-policy','access-control-allow-origin'}}
                    result_headers['Content-Security-Policy'] = 'sandbox allow-scripts allow-same-origin allow-forms allow-popups allow-downloads'
                    result_headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
                    result_headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(self)'
                    return web.Response(status=upstream.status, body=await upstream.read(), headers=result_headers)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                return web.Response(status=503, text='Published app temporarily unavailable.')
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
                result_headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
                result_headers['Cache-Control'] = 'no-store'
                result_headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(self)'
                if upstream.status==200 and 'text/html' in upstream.headers.get('Content-Type',''):
                    content=inject(await upstream.read(),result_headers)
                    return web.Response(status=upstream.status,body=content,headers=result_headers)
                response = web.StreamResponse(status=upstream.status, headers=result_headers)
                await response.prepare(request)
                async for chunk in upstream.content.iter_chunked(65536):
                    await response.write(chunk)
                await response.write_eof()
                return response
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return web.Response(status=503, text='Preview is temporarily offline. Reconnect from GeneSys.', headers={'Cache-Control': 'no-store'})

    async def health(request):
        return web.json_response({'status': 'ok', 'deploymentId': os.getenv('RAILWAY_DEPLOYMENT_ID', '')})
    app.router.add_get('/health', health)
    app.router.add_post('/internal/previews', register)
    app.router.add_route('*', '/{path:.*}', proxy)
    return app


if __name__ == '__main__':
    # Do not log capability URLs or signed upstream addresses.
    web.run_app(create_app(), host='0.0.0.0', port=int(os.getenv('PORT', '8080')), access_log=None)
