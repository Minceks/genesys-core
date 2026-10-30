from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.daytona_workspace import DaytonaWorkspace


@pytest.fixture
def workspace(monkeypatch):
    workspace = DaytonaWorkspace.__new__(DaytonaWorkspace)
    workspace.project_id = 'test-project'
    workspace.name = 'test-sandbox'
    workspace.sandbox = SimpleNamespace(
        id='sandbox-id', state='stopped', recoverable=False,
        refresh_data=Mock(),
        fs=SimpleNamespace(get_file_info=Mock(), upload_file=Mock()),
        process=SimpleNamespace(exec=Mock(return_value=SimpleNamespace(exit_code=0))),
    )
    workspace.sandbox.start = Mock(side_effect=lambda **_: setattr(workspace.sandbox, 'state', 'started'))
    workspace.client = SimpleNamespace(get=Mock(return_value=workspace.sandbox))
    monkeypatch.setattr('agent.daytona_workspace.time.sleep', lambda _: None)
    return workspace


def test_write_starts_stopped_sandbox(workspace):
    result = workspace.write_file('design/brief.json', '{}')
    workspace.sandbox.start.assert_called_once_with(timeout=60)
    assert result['status'] == 'success'
    workspace.sandbox.fs.upload_file.assert_called_once_with(
        b'{}', 'workspace/genesys-project/design/brief.json', timeout=120,
    )


@pytest.mark.parametrize('stage', ['mkdir', 'upload'])
def test_write_retries_container_not_ready(workspace, stage):
    operation = workspace.sandbox.process.exec if stage == 'mkdir' else workspace.sandbox.fs.upload_file
    operation.side_effect = [
        RuntimeError('SANDBOX_NOT_RUNNING: failed to resolve container IP after 3 attempts'),
        SimpleNamespace(exit_code=0),
    ]
    assert workspace.write_file('design/brief.json', '{}')['status'] == 'success'
    assert operation.call_count == 2
    assert workspace.client.get.call_count == 2


def test_write_stops_retrying_unavailable_sandbox(workspace):
    workspace.sandbox.process.exec.side_effect = RuntimeError('SANDBOX_NOT_RUNNING')
    with pytest.raises(RuntimeError, match='SANDBOX_NOT_RUNNING'):
        workspace.write_file('design/brief.json', '{}')
    assert workspace.sandbox.process.exec.call_count == 3
    workspace.sandbox.fs.upload_file.assert_not_called()


def test_write_does_not_retry_unrelated_errors(workspace):
    workspace.sandbox.process.exec.side_effect = RuntimeError('permission denied')
    with pytest.raises(RuntimeError, match='permission denied'):
        workspace.write_file('design/brief.json', '{}')
    assert workspace.sandbox.process.exec.call_count == 1
    workspace.sandbox.fs.upload_file.assert_not_called()
