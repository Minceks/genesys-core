import datetime
import json
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import httpx
import pytest

from agent import deployment_smoke as smoke
from tests.test_preview_hosting import storage, Workspace
from tests.test_user_auth import authenticated_backend


def test_targets_come_from_active_disk_snapshots_without_waking_sandboxes(storage):
    from agent import preview_hosting as hosting
    hosting.save(Workspace(), 'active')
    hosting.save(Workspace(), 'deleted'); hosting.disable('deleted')
    (hosting.root() / 'not-a-project').mkdir()
    targets = smoke.saved_targets()
    assert targets == [{'ticket': hosting.ticket_for('active'), 'url': hosting.available_url('active')}]


def test_http_probe_checks_real_local_assets_and_never_follows_external_or_redirect_targets():
    calls = []
    def serve(request):
        calls.append(str(request.url))
        if request.url.path == '/':
            return httpx.Response(200, headers={'content-type': 'text/html'}, text='''<html><script src="/assets/app.js"></script>
                <link rel="stylesheet" href="assets/app.css"><link rel="icon" href="/icon.svg">
                <script src="http://127.0.0.1/private"></script></html>''')
        mime = {'/assets/app.js': 'application/javascript', '/assets/app.css': 'text/css', '/icon.svg': 'image/svg+xml'}[request.url.path]
        return httpx.Response(200, headers={'content-type': mime}, text='fixture')
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        result = smoke.check_http('https://project.example.test/', time.monotonic() + 10, client)
    assert len(result['assetsChecked']) == 3 and result['externalAssetsSkipped'] == 1
    assert all(url.startswith('https://project.example.test/') for url in calls)
    calls.clear()
    with httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request.url) or
            httpx.Response(302, headers={'location': 'https://untrusted.example.test/'}))) as client:
        with pytest.raises(ValueError, match='302'):
            smoke.check_http('https://project.example.test/', time.monotonic() + 10, client)
    assert len(calls) == 1


def test_preview_page_is_checked_as_a_browser_receives_it():
    seen = []
    def serve(request):
        seen.append(request.headers)
        return httpx.Response(200, headers={'content-type': 'text/html'}, content=b'\x1f\x8b\x08compressed<script data-genesys-selection></script>')
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        with pytest.raises(ValueError, match='did not return HTML'):
            smoke.check_http('https://project.example.test/', time.monotonic() + 10, client)
    assert 'range' not in seen[0]


@pytest.mark.parametrize('failure', ['missing', 'html-instead-of-js', 'empty'])
def test_asset_failures_cannot_pass_as_a_healthy_deployment(failure):
    def serve(request):
        if request.url.path == '/':
            return httpx.Response(200, headers={'content-type': 'text/html'}, text='<html><script src="/app.js"></script></html>')
        if failure == 'missing': return httpx.Response(404)
        return httpx.Response(200, headers={'content-type': 'text/html' if failure == 'html-instead-of-js' else 'application/javascript'},
                              text='<html>Fallback</html>' if failure == 'html-instead-of-js' else '')
    with httpx.Client(transport=httpx.MockTransport(serve)) as client:
        with pytest.raises(ValueError): smoke.check_http('https://project.example.test/', time.monotonic() + 10, client)


def test_manager_deduplicates_deployment_triggers_and_persists_failed_checks(storage, monkeypatch):
    callbacks = []
    monkeypatch.delenv('RAILWAY_DEPLOYMENT_ID', raising=False)
    monkeypatch.setattr(smoke.threading, 'Thread', lambda **kwargs: SimpleNamespace(start=lambda: callbacks.append(kwargs['target'])))
    monkeypatch.setattr(smoke.time, 'sleep', lambda _: None)
    monkeypatch.setattr(smoke, 'run_checks', lambda: {'status': 'failed', 'checkedAt': 123,
                                                     'projects': [{'ticket': '0' * 32, 'status': 'failed', 'error': 'Asset HTTP 404'}]})
    manager = smoke.DeploymentChecks()
    assert manager.schedule('frontend:one')
    assert not manager.schedule('frontend:one')
    assert manager.schedule('preview-router:one')
    assert len(callbacks) == 1
    callbacks[0]()
    assert manager.summary() == {'status': 'failed', 'projectsChecked': 1, 'failed': 1, 'checkedAt': 123}
    from agent.preview_hosting import root
    saved = json.loads((root().parent / 'deployment-smoke/latest.json').read_text())
    assert saved['triggers'] == ['frontend:one', 'preview-router:one']
    assert 'ticket' not in json.dumps(manager.summary())


def test_smoke_trigger_requires_server_secret_and_does_not_accept_public_auth(authenticated_backend, monkeypatch):
    monkeypatch.setenv('GENESYS_DEPLOY_SMOKE_KEY', 'fixture-deployment-smoke-key-' * 2)
    client = authenticated_backend
    assert client.post('/internal/deployment-smoke', json={'source': 'frontend', 'deploymentId': 'one'}).status_code == 401
    assert client.get('/internal/deployment-smoke', headers={'Authorization': 'Bearer owner'}).status_code == 401
    calls = []
    monkeypatch.setattr(smoke.checks, 'schedule', lambda source: calls.append(source) or True)
    headers = {'X-GeneSys-Smoke-Key': 'fixture-deployment-smoke-key-' * 2}
    response = client.post('/internal/deployment-smoke', headers=headers, json={'source': 'frontend', 'deploymentId': 'release-one'})
    assert response.status_code == 202 and calls == ['frontend:release-one']
    assert client.post('/internal/deployment-smoke', headers=headers,
                       json={'source': 'arbitrary', 'deploymentId': 'release-one'}).status_code == 400


def test_failed_probe_is_persisted_without_requeuing_the_same_trigger(storage, monkeypatch):
    callbacks = []
    monkeypatch.delenv('RAILWAY_DEPLOYMENT_ID', raising=False)
    monkeypatch.setattr(smoke.threading, 'Thread', lambda **kwargs: SimpleNamespace(start=lambda: callbacks.append(kwargs['target'])))
    monkeypatch.setattr(smoke.time, 'sleep', lambda _: None)
    def unavailable(): raise RuntimeError('Probe failed')
    monkeypatch.setattr(smoke, 'run_checks', unavailable)
    manager = smoke.DeploymentChecks(); manager.schedule('backend:one'); callbacks[0]()
    assert manager.report['status'] == 'failed'
    assert len(callbacks) == 1 and not manager.pending and not manager.running
    from agent.preview_hosting import root
    assert json.loads((root().parent / 'deployment-smoke/latest.json').read_text())['status'] == 'failed'


def test_frontend_notifies_only_after_its_own_version_is_live_and_keeps_secret_server_side(monkeypatch):
    import deployment_notify as notify
    for key, value in {'RAILWAY_ENVIRONMENT_ID': 'fixture', 'RAILWAY_DEPLOYMENT_ID': 'frontend-release',
            'GENESYS_DEPLOY_SMOKE_KEY': 'fixture-smoke-key-' * 3, 'GENESYS_SMOKE_BACKEND_URL': 'https://backend.example.test',
            'GENESYS_SMOKE_FRONTEND_URL': 'https://frontend.example.test', 'GENESYS_DEPLOY_SMOKE_ENABLED': '1'}.items():
        monkeypatch.setenv(key, value)
    calls = []
    class Reply:
        def __init__(self, status): self.status = status
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, _): return b'{"deploymentId":"frontend-release"}'
    def request(value, **kwargs):
        calls.append(value)
        return Reply(202 if value.data else 200)
    monkeypatch.setattr(notify, 'build_opener', lambda *args: SimpleNamespace(open=request))
    monkeypatch.setattr(notify.threading, 'Thread', lambda **kwargs: SimpleNamespace(start=kwargs['target']))
    notify.notify_deployment()
    assert calls[0].full_url == 'https://frontend.example.test/health'
    assert not calls[0].has_header('X-genesys-smoke-key')
    assert calls[1].full_url == 'https://backend.example.test/internal/deployment-smoke'
    assert calls[1].headers['X-genesys-smoke-key'] == 'fixture-smoke-key-' * 3
    assert json.loads(calls[1].data) == {'source': 'frontend', 'deploymentId': 'frontend-release'}
    assert notify.NoRedirects().redirect_request(None, None, None, None, None, None) is None


def test_router_notification_checks_concrete_wildcard_origin_before_notifying(monkeypatch):
    import asyncio
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('genesys_router_smoke_test',
        Path(__file__).resolve().parents[1] / 'preview_proxy/server.py')
    server = importlib.util.module_from_spec(spec); spec.loader.exec_module(server)
    for key, value in {'RAILWAY_ENVIRONMENT_ID': 'fixture', 'RAILWAY_DEPLOYMENT_ID': 'router-release',
            'RAILWAY_PUBLIC_DOMAIN': '*.previews.example.test', 'GENESYS_PREVIEW_DOMAIN': 'previews.example.test',
            'GENESYS_PREVIEW_PROXY_KEY': 'fixture-proxy-key-' * 3, 'GENESYS_DEPLOY_SMOKE_KEY': 'fixture-smoke-key-' * 3,
            'GENESYS_SMOKE_BACKEND_URL': 'https://backend.example.test', 'GENESYS_DEPLOY_SMOKE_ENABLED': '1'}.items():
        monkeypatch.setenv(key, value)
    calls = []
    class Reply:
        def __init__(self, status): self.status = status
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def json(self): return {'deploymentId': 'router-release'}
    class Client:
        def get(self, url, **kwargs): calls.append(('GET', url, kwargs)); return Reply(200)
        def post(self, url, **kwargs): calls.append(('POST', url, kwargs)); return Reply(202)
        async def close(self): pass
    monkeypatch.setattr(server.aiohttp, 'ClientSession', lambda **kwargs: Client())
    async def run():
        app = server.create_app(); lifecycle = app.cleanup_ctx[0](app)
        await anext(lifecycle); await asyncio.sleep(0)
        try: await anext(lifecycle)
        except StopAsyncIteration: pass
    asyncio.run(run())
    assert calls[0][1] == 'https://deployment-check.previews.example.test/health'
    assert 'headers' not in calls[0][2]
    assert calls[1][1] == 'https://backend.example.test/internal/deployment-smoke'
    assert calls[1][2]['json'] == {'source': 'preview-router', 'deploymentId': 'router-release'}


def test_real_browser_probe_opens_phone_and_desktop_without_sending_write_requests(tmp_path, monkeypatch):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    import ipaddress
    import playwright.sync_api
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = tmp_path / 'fixture.crt', tmp_path / 'fixture.key'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(('GET', self.path))
            self.send_response(200); self.send_header('Content-Type', 'text/html'); self.end_headers()
            self.wfile.write(b'''<html><body><h1>A saved project</h1><p>Available after deployment.</p>
              <script>fetch('/must-not-write',{method:'POST'}).catch(()=>{});</script></body></html>''')
        def do_POST(self):
            requests.append(('POST', self.path)); self.send_response(200); self.end_headers()
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(cert_path, key_path)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    # Trust the ephemeral local fixture only. Production contexts retain TLS validation.
    original = playwright.sync_api.Browser.new_context
    monkeypatch.setattr(playwright.sync_api.Browser, 'new_context', lambda self, **kwargs:
                        original(self, **{**kwargs, 'ignore_https_errors': True}))
    try:
        result = smoke.check_browser(f'https://127.0.0.1:{server.server_port}/', time.monotonic() + 30)
        assert [item['width'] for item in result['viewports']] == [1280, 390]
        assert result['blockedRequests'] == 2
        assert all(method == 'GET' for method, path in requests)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
