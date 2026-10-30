from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from agent import builder_modes


@pytest.mark.parametrize('mode', ['plan', 'discuss'])
def test_imperative_request_in_read_only_mode_never_opens_workspace(monkeypatch, tmp_path, mode):
    from agent import orchestrator
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'jobs.sqlite3'))
    provider = SimpleNamespace(generate=Mock(return_value=SimpleNamespace(text='A proposed change, not applied.')))
    monkeypatch.setattr(orchestrator, 'get_provider', lambda: provider)
    workspace = Mock(side_effect=AssertionError('Cannot create or open a writable workspace'))
    monkeypatch.setattr(orchestrator, 'get_workspace', workspace)
    monkeypatch.setattr(builder_modes, 'read_project_context', lambda _, prompt='': {})
    result = orchestrator.run_agent('/' + mode + ' Replace all files with a new website', 'project')
    assert result['mode'] == mode
    assert not result['modifiedFiles'] and not result['buildAttempted']
    assert provider.generate.call_args.args[1] == []
    workspace.assert_not_called()
    assert bool(result['proposedBuildPrompt']) == (mode == 'plan')


def test_context_reader_only_downloads_allowlisted_existing_files(monkeypatch):
    from agent import daytona_workspace
    downloads = Mock(return_value=b'export default function App() {}')
    client = SimpleNamespace(get=Mock(return_value=SimpleNamespace(fs=SimpleNamespace(download_file=downloads))))
    monkeypatch.setattr(daytona_workspace, 'get_daytona', lambda: client)
    assert builder_modes.read_project_context('project')
    assert all('.env' not in call.args[0] for call in downloads.call_args_list)


@pytest.mark.parametrize('mode', ['invalid', {}, []])
def test_invalid_modes_rejected(mode):
    with pytest.raises(ValueError):
        builder_modes.encode_mode('request', mode)
