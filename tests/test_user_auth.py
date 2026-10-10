import pytest
from agent import user_auth

OWNER = '10000000-0000-4000-8000-000000000001'
OTHER = '20000000-0000-4000-8000-000000000002'
PROJECT = '30000000-0000-4000-8000-000000000003'


@pytest.fixture
def authenticated_backend(monkeypatch):
    import cloud_agent
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test')
    monkeypatch.setenv('GENESYS_PROMOTION_ADMIN_IDS', '')
    def call(method, path, token, **kwargs):
        if path == '/auth/v1/user':
            if token not in {'owner', 'other'}:
                raise user_auth.AccessError('Invalid or expired session.', 401)
            return {'id': OWNER if token == 'owner' else OTHER}
        if method == 'POST':
            assert kwargs['json']['owner_id'] == OWNER
            return [{'id': PROJECT, **kwargs['json']}]
        return [{'id': PROJECT, 'owner_id': OWNER}] if token == 'owner' else []
    monkeypatch.setattr(user_auth, 'call', call)
    return cloud_agent.app.test_client()


@pytest.mark.parametrize('path,method', [('/list-files','GET'),('/read-file','GET'),
    ('/write-file','POST'),('/agent/run','POST'),('/agent/jobs','POST'),
    ('/agent/jobs/unknown','GET'),('/preview','POST'),('/promote','POST')])
def test_other_user_cannot_access_project(authenticated_backend, path, method):
    response = authenticated_backend.open(path + '?projectId=' + PROJECT, method=method,
        headers={'Authorization': 'Bearer other'}, json={'projectId': PROJECT})
    assert response.status_code == 404


def test_key_does_not_bypass_session_and_expired_session_denied(authenticated_backend):
    assert authenticated_backend.get('/list-files', headers={'X-API-Key':'anything'}).status_code == 401
    assert authenticated_backend.get('/api/projects/' + PROJECT, headers={'Authorization':'Bearer expired'}).status_code == 401


def test_owner_can_create_and_read_and_cannot_spoof_owner(authenticated_backend):
    headers = {'Authorization':'Bearer owner'}
    assert authenticated_backend.get('/api/projects/' + PROJECT, headers=headers).status_code == 200
    response = authenticated_backend.post('/api/projects', headers=headers, json={'name':'My project','owner_id':OTHER})
    assert response.status_code == 201
    assert response.json['owner_id'] == OWNER


def test_non_admin_cannot_promote(authenticated_backend):
    response = authenticated_backend.post('/promote', headers={'Authorization':'Bearer owner'}, json={'projectId':PROJECT})
    assert response.status_code == 403


def test_invalid_uuid_is_hidden(authenticated_backend):
    assert authenticated_backend.get('/api/projects/not-a-uuid', headers={'Authorization':'Bearer owner'}).status_code == 404
