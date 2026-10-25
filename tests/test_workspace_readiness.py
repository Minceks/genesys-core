from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from agent.daytona_workspace import DaytonaWorkspace
from tests.test_daytona_file_recovery import workspace


def test_prepare_wakes_cached_workspace_and_waits_for_real_container(workspace):
    workspace.sandbox.process.exec.side_effect=[RuntimeError('SANDBOX_NOT_RUNNING: failed to resolve container IP'),
        RuntimeError('failed to resolve container IP after 3 attempts'),SimpleNamespace(exit_code=0)]
    workspace.prepare()
    workspace.sandbox.start.assert_called_once_with(timeout=60)
    assert workspace.sandbox.process.exec.call_count==3
    assert all(call.args==('true',) for call in workspace.sandbox.process.exec.call_args_list)
    assert workspace._prepared_at is not None
    workspace.prepare()  # Capture immediately after preparation reuses the readiness proof.
    assert workspace.sandbox.process.exec.call_count==3
    workspace._prepared_at-=6
    workspace.sandbox.state='stopped';workspace.sandbox.process.exec.side_effect=None
    workspace.sandbox.process.exec.return_value=SimpleNamespace(exit_code=0)
    workspace.prepare()
    assert workspace.sandbox.start.call_count==2


def test_prepare_handles_started_metadata_without_a_container_ip(workspace):
    workspace.sandbox.state='started'
    workspace.sandbox.process.exec.side_effect=[RuntimeError('failed to resolve container IP after 3 attempts'),SimpleNamespace(exit_code=0)]
    workspace.prepare()
    workspace.sandbox.start.assert_not_called()
    assert workspace.sandbox.process.exec.call_count==2


def test_prepare_stops_after_bounded_readiness_attempts(workspace):
    workspace.sandbox.process.exec.side_effect=RuntimeError('SANDBOX_NOT_RUNNING')
    with pytest.raises(RuntimeError,match='SANDBOX_NOT_RUNNING'):workspace.prepare()
    assert workspace.sandbox.process.exec.call_count==8
    assert workspace._prepared_at is None


def test_prepare_does_not_retry_permission_errors(workspace):
    workspace.sandbox.process.exec.side_effect=RuntimeError('permission denied')
    with pytest.raises(RuntimeError,match='permission denied'):workspace.prepare()
    assert workspace.sandbox.process.exec.call_count==1


@pytest.mark.parametrize('where',['lookup','wake'])
def test_an_unavailable_existing_editor_is_never_recreated(workspace,where):
    workspace.client.create=Mock()
    if where=='lookup':workspace.client.get.side_effect=RuntimeError('authentication failed')
    else:workspace.sandbox.start.side_effect=RuntimeError('Sandbox infrastructure unavailable')
    with pytest.raises(RuntimeError):workspace._get_or_create()
    workspace.client.create.assert_not_called()


def test_confirmed_missing_sandbox_can_still_be_created(workspace):
    from daytona.common.errors import DaytonaNotFoundError
    workspace.client.get.side_effect=[DaytonaNotFoundError('Sandbox does not exist',status_code=404),workspace.sandbox]
    workspace.sandbox.state='started';workspace.client.create=Mock(return_value=workspace.sandbox)
    workspace._clone_project=Mock()
    assert workspace._get_or_create() is workspace.sandbox
    workspace.client.create.assert_called_once()
    workspace._clone_project.assert_called_once()
    assert workspace._prepared_at is not None


def test_missing_container_does_not_become_a_missing_source_file(workspace):
    workspace.sandbox.fs.download_file=Mock(side_effect=[RuntimeError('SANDBOX_NOT_RUNNING'),b'preserved source'])
    result=workspace.read_file('src/App.jsx')
    assert result['content']=='preserved source'
    workspace.sandbox.start.assert_called_once()
    workspace.sandbox.fs.download_file.side_effect=RuntimeError('SANDBOX_NOT_RUNNING')
    with pytest.raises(RuntimeError,match='SANDBOX_NOT_RUNNING'):workspace.read_file('src/App.jsx')


def test_build_prepares_workspace_before_saving_its_source(monkeypatch):
    from agent import orchestrator
    events=[]
    workspace=SimpleNamespace(prepare=lambda:events.append('ready'))
    monkeypatch.setattr(orchestrator,'get_workspace',lambda _:workspace)
    monkeypatch.setattr(orchestrator,'get_provider',lambda:SimpleNamespace())
    monkeypatch.setattr('agent.builder_controls.get_controls',lambda _: {})
    def capture(*_,**__):events.append('backup');raise RuntimeError('End fixture before any generation')
    monkeypatch.setattr('agent.version_history.operate',capture)
    result=orchestrator.run_agent('Build a redesigned game','00000000-0000-4000-8000-000000000001')
    assert events==['ready','backup']
    assert result['errorType']=='version_backup' and not result['modifiedFiles']


def test_failed_editor_request_preserves_durable_preview_without_touching_sandbox(monkeypatch):
    import cloud_agent
    monkeypatch.setattr(cloud_agent,'run_agent',lambda **_: {'status':'error','requestType':'build',
        'errorType':'workspace_unavailable','message':'Editor unavailable','modifiedFiles':[]})
    monkeypatch.setattr('agent.preview_hosting.available_url',lambda _: 'https://saved.previews.example.test/')
    def forbidden(*_,**__):raise AssertionError('Saved preview fallback must not access an editor sandbox')
    monkeypatch.setattr(cloud_agent,'get_workspace',forbidden)
    monkeypatch.setattr(cloud_agent,'verified_preview',forbidden)
    result=cloud_agent._execute_agent_request('Redesign the game','project',[])
    assert result['status']=='error' and result['errorType']=='workspace_unavailable'
    assert result['previewUrl']=='https://saved.previews.example.test/'
    assert result['previewPersistent'] and result['previousPreviewPreserved']
    assert not result.get('previewHostingError')
