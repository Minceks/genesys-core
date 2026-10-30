from unittest.mock import Mock
import pytest
from agent.builder_controls import get_controls, save_controls, assert_writable, ControlsConflict, normalize_controls
from agent.daytona_workspace import DaytonaWorkspace


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv('GENESYS_JOB_DB', str(tmp_path / 'jobs.sqlite3'))


def test_controls_persist_per_project_and_enforce_only_selected_paths():
    saved = save_controls('a', {'instructions': 'Keep the existing brand.', 'lockedPaths': ['src/brand/', 'src/App.jsx'], 'revision': 0})
    assert get_controls('a') == saved
    assert get_controls('b')['lockedPaths'] == []
    with pytest.raises(ValueError, match='Frozen file'):
        assert_writable('a', 'src/brand/colors.css')
    assert_writable('a', 'src/brand-new/colors.css')
    assert_writable('b', 'src/App.jsx')
    with pytest.raises(ControlsConflict):
        save_controls('a', {'revision': 0})


def test_frozen_write_is_blocked_before_remote_io():
    project = '10000000-0000-4000-8000-000000000001'
    save_controls(project, {'instructions': '', 'lockedPaths': ['src/App.jsx'], 'revision': 0})
    workspace = DaytonaWorkspace.__new__(DaytonaWorkspace)
    workspace.project_id = project
    workspace._ensure_sandbox_running = Mock(side_effect=AssertionError('Remote I/O must not run'))
    with pytest.raises(ValueError, match='Frozen file'):
        workspace.write_file('src/App.jsx', 'export default () => null')
    workspace._ensure_sandbox_running.assert_not_called()


@pytest.mark.parametrize('path', ['../secret', '/etc/config', 'C:/private', 'src/*.jsx', './/', 'src/../../private'])
def test_invalid_frozen_paths_rejected(path):
    with pytest.raises(ValueError):
        normalize_controls({'lockedPaths': [path]})


def test_controls_cannot_change_during_queued_or_running_job():
    from agent.beta_storage import connection
    with connection() as db:
        db.execute('CREATE TABLE jobs(project TEXT, state TEXT)')
        db.execute("INSERT INTO jobs VALUES('a','running')")
    with pytest.raises(ControlsConflict, match='current build'):
        save_controls('a', {'revision': 0})
