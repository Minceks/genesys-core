from tests.test_user_auth import authenticated_backend,PROJECT
import pytest


@pytest.mark.parametrize('path,method',[('/builder/history','GET'),('/builder/history','POST'),('/builder/app-backend','POST')])
def test_new_workflows_require_project_ownership(authenticated_backend,path,method):
    response=authenticated_backend.open(path+'?projectId='+PROJECT,method=method,
        headers={'Authorization':'Bearer other'},json={'projectId':PROJECT})
    assert response.status_code==404


def test_history_rejects_active_build_before_remote_io(authenticated_backend,monkeypatch):
    import cloud_agent
    monkeypatch.setattr(cloud_agent.jobs,'is_running',lambda _:True)
    response=authenticated_backend.post('/builder/history',headers={'Authorization':'Bearer owner'},
        json={'projectId':PROJECT,'versionId':'a'*32})
    assert response.status_code==409
