import pytest
from tests.test_user_auth import authenticated_backend, PROJECT


@pytest.mark.parametrize('method', ['GET', 'PUT'])
def test_other_project_owner_cannot_read_or_change_ai_controls(authenticated_backend, method):
    response = authenticated_backend.open('/builder/controls?projectId=' + PROJECT, method=method,
        headers={'Authorization': 'Bearer other'}, json={'projectId': PROJECT, 'revision': 0})
    assert response.status_code == 404


def test_owner_can_save_and_read_controls(authenticated_backend, monkeypatch, tmp_path):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'controls.sqlite3'))
    headers = {'Authorization': 'Bearer owner'}
    response = authenticated_backend.put('/builder/controls', headers=headers,
        json={'projectId': PROJECT, 'instructions': 'Keep typography.', 'lockedPaths': ['src/brand/'], 'revision': 0})
    assert response.status_code == 200
    assert response.json['revision'] == 1
    response = authenticated_backend.get('/builder/controls?projectId=' + PROJECT, headers=headers)
    assert response.json['instructions'] == 'Keep typography.'
