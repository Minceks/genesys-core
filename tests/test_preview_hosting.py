import io
import json
import tarfile
from types import SimpleNamespace

import pytest

from agent import preview_hosting as hosting
from tests.test_user_auth import authenticated_backend, PROJECT


def archive(files):
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode='w') as bundle:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            data = content.encode()
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
    return result.getvalue()


class Workspace:
    def __init__(self):
        self.proof = {'checkpointId': 'verified-1', 'commit': 'commit-1'}
        self.blob = archive({'index.html': '<h1>Completed</h1>', 'assets/first.js': 'first', 'favicon.svg': '<svg/>'})
        self.exports = 0
        self.sandbox = SimpleNamespace(process=SimpleNamespace(exec=self.execute),
                                       fs=SimpleNamespace(download_file=lambda _: self.blob))

    def _ensure_sandbox_running(self): pass

    def execute(self, command, **_):
        if command.startswith('cat '):
            return SimpleNamespace(exit_code=0, result=json.dumps(self.proof))
        if command.startswith('stat '):
            return SimpleNamespace(exit_code=0, result=str(len(self.blob)))
        if command.startswith('tar '): self.exports += 1
        return SimpleNamespace(exit_code=0, result='')


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH', str(tmp_path))
    monkeypatch.setenv('GENESYS_PREVIEW_DOMAIN', 'previews.example.test')
    monkeypatch.setenv('GENESYS_PREVIEW_PROXY_KEY', 'preview-test-key-' * 3)
    return tmp_path


def test_completed_snapshot_survives_new_process_lookup_and_keeps_origin_and_old_chunks(storage):
    workspace = Workspace()
    url = hosting.save(workspace, PROJECT)
    assert hosting.available_url(PROJECT) == url
    assert hosting.save(workspace, PROJECT) == url and workspace.exports == 1
    workspace.proof = {'checkpointId': 'verified-2', 'commit': 'commit-2'}
    workspace.blob = archive({'index.html': '<h1>Updated</h1>', 'assets/second.js': 'second'})
    assert hosting.save(workspace, PROJECT) == url
    active = hosting.directory(hosting.ticket_for(PROJECT))
    assert (active / 'assets/first.js').read_text() == 'first'
    assert (active / 'assets/second.js').read_text() == 'second'
    assert 'Updated' in (active / 'index.html').read_text()
    assert hosting.available_url('another-project') is None
    hosting.disable(PROJECT)
    assert hosting.available_url(PROJECT) is None


@pytest.mark.parametrize('files', [ {'../escape': 'bad', 'index.html': 'bad'},
    {'.env': 'private', 'index.html': 'bad'}, {'assets/only.js': 'missing index'} ])
def test_invalid_export_preserves_last_completed_version(storage, files):
    workspace = Workspace()
    url = hosting.save(workspace, PROJECT)
    workspace.proof = {'checkpointId': 'bad', 'commit': 'bad'}
    workspace.blob = archive(files)
    with pytest.raises(ValueError): hosting.save(workspace, PROJECT)
    assert hosting.available_url(PROJECT) == url
    assert 'Completed' in (hosting.directory(hosting.ticket_for(PROJECT)) / 'index.html').read_text()


def test_storage_limit_does_not_replace_previous_build(storage, monkeypatch):
    workspace = Workspace()
    url = hosting.save(workspace, PROJECT)
    workspace.proof = {'checkpointId': 'too-big', 'commit': 'too-big'}
    monkeypatch.setattr(hosting, 'MAX_STORAGE', 1)
    with pytest.raises(ValueError, match='storage is full'): hosting.save(workspace, PROJECT)
    assert hosting.available_url(PROJECT) == url


def test_reopening_owner_project_uses_disk_without_touching_daytona_even_during_build(storage, authenticated_backend, monkeypatch):
    import cloud_agent
    url = hosting.save(Workspace(), PROJECT)
    monkeypatch.setattr(cloud_agent, 'get_workspace', lambda *_: pytest.fail('Must not wake sandbox'))
    monkeypatch.setattr(cloud_agent.jobs, 'is_running', lambda *_: True)
    result = authenticated_backend.post('/preview', headers={'Authorization': 'Bearer owner'}, json={'projectId': PROJECT})
    assert result.status_code == 200 and result.json['url'] == url and result.json['persistent']
    denied = authenticated_backend.post('/preview', headers={'Authorization': 'Bearer other'}, json={'projectId': PROJECT})
    assert denied.status_code == 404


def test_internal_assets_require_proxy_key_and_support_deep_routes_without_leaking_metadata(storage, authenticated_backend):
    hosting.save(Workspace(), PROJECT)
    prefix = '/internal/preview-builds/' + hosting.ticket_for(PROJECT) + '/'
    assert authenticated_backend.get(prefix).status_code == 401
    headers = {'X-GeneSys-Proxy-Key': 'preview-test-key-' * 3}
    assert authenticated_backend.get(prefix, headers=headers).status_code == 200
    assert authenticated_backend.get(prefix+'favicon.svg', headers=headers).status_code == 200
    assert authenticated_backend.get(prefix+'assets/first.js', headers=headers).data == b'first'
    response = authenticated_backend.get(prefix+'products/one', headers={**headers,'Accept':'text/html'})
    assert response.status_code == 200 and b'Completed' in response.data
    for path in ['assets/missing.js', '.proof.json', '../.active']:
        response = authenticated_backend.get(prefix+path, headers={**headers,'Accept':'text/html'})
        assert response.status_code == 404
    assert authenticated_backend.post(prefix, headers=headers).status_code == 405


def test_preview_proxy_serves_saved_build_after_expiry_and_process_restart(storage, authenticated_backend, monkeypatch):
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('preview_server', Path(__file__).resolve().parents[1]/'preview_proxy/server.py')
    proxy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(proxy)
    url = hosting.save(Workspace(), PROJECT)
    host = url.split('/')[2]
    monkeypatch.setenv('GENESYS_PUBLISHED_BACKEND_URL', 'https://backend.example.test')
    requests = []
    class Response:
        def __init__(self, path, headers):
            result = authenticated_backend.get(path, headers=headers)
            self.status, self.headers, self.body = result.status_code, result.headers, result.data
        async def __aenter__(self): return self
        async def __aexit__(self, *_): pass
        async def read(self): return self.body
    class Backend:
        def request(self, method, url, **kw):
            requests.append(kw['headers'])
            return Response(url.replace('https://backend.example.test',''), kw['headers'])
        async def close(self): pass
    async def run():
        for restarted in (False, True):
            client = TestClient(TestServer(proxy.create_app()))
            await client.start_server()
            original = client.server.app['client']
            await original.close()
            client.server.app['client'] = Backend()
            try:
                monkeypatch.setattr(proxy, 'time', SimpleNamespace(monotonic=lambda: 999999999999))
                response = await client.get('/', headers={'Host':host, 'Authorization':'Bearer user', 'Cookie':'private=session'})
                assert response.status == 200 and 'Completed' in await response.text()
                assert 'allow-same-origin' in response.headers['Content-Security-Policy']
                assert response.headers['Permissions-Policy'] == 'camera=(), microphone=(), geolocation=(self)'
                assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
                response = await client.get('/assets/first.js', headers={'Host':host})
                assert response.status == 200 and await response.text() == 'first'
                response = await client.get('/assets/no.js', headers={'Host':host})
                assert response.status == 404
                response = await client.get('/', headers={'Host':'0'*32+'.previews.example.test'})
                assert response.status == 410
            finally: await client.close()
    asyncio.run(run())
    assert all('Authorization' not in h and 'Cookie' not in h for h in requests)


def test_legacy_migration_skips_archived_and_active_projects_and_is_idempotent(storage, monkeypatch):
    from scripts import migrate_completed_previews as migration
    from agent.beta_storage import connection
    monkeypatch.setenv('GENESYS_JOB_DB', str(storage/'migration.sqlite3'))
    with connection() as db:
        db.execute('CREATE TABLE jobs(project TEXT, state TEXT)')
        db.executemany('INSERT INTO jobs VALUES(?,?)', [('old','completed'), ('archived','failed'), ('active','running')])
    workspace = Workspace()
    looked_up = []
    def lookup(name):
        looked_up.append(name)
        return SimpleNamespace(state='archived' if name.endswith('archived') else 'started')
    monkeypatch.setattr(migration, 'sandbox_name_for_project', lambda project: project)
    monkeypatch.setattr(migration, 'get_daytona', lambda: SimpleNamespace(get=lookup))
    monkeypatch.setattr(migration, 'get_workspace', lambda project: workspace if project=='old' else pytest.fail('Archived workspace must not reopen'))
    result = migration.main()
    assert result['saved'] == ['old'] and result['skipped'][0]['errorType'] == 'ArchivedWorkspace'
    assert 'active' not in looked_up
    assert (hosting.root().parent/'preview-migration-v1.json').is_file()
    result = migration.main()
    assert result['alreadySaved'] == 1 and workspace.exports == 1
    workspace.proof = {'checkpointId':'updated', 'commit':'updated'}
    workspace.blob = archive({'index.html':'<h1>Updated manually verified snapshot</h1>'})
    captures=[]
    monkeypatch.setattr('agent.version_history.operate',lambda workspace,action,**kw:captures.append(action))
    result = migration.main(projects=['old','active'], refresh=True)
    assert captures == ['capture']
    assert result['saved'] == ['old'] and result['skipped'][0]['errorType'] == 'ActiveBuild'
    assert 'Updated manually' in (hosting.directory(hosting.ticket_for('old'))/'index.html').read_text()
