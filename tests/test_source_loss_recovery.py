import json,shlex,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from agent import version_history as history


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    from agent import daytona_workspace
    root=tmp_path/'sandbox/project';(root/'src').mkdir(parents=True)
    (root/'src/App.jsx').write_text('saved working source')
    (root/'.env').write_text('private runtime configuration')
    monkeypatch.setattr(daytona_workspace,'REMOTE_PROJECT_ROOT',str(root))
    monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH',str(tmp_path/'volume'))
    def execute(command,**kwargs):
        args=shlex.split(command)
        if args[:2]==['test','-f']:return SimpleNamespace(exit_code=0 if Path(args[2]).is_file() else 1,result='')
        if args[:2]==['rm','-f']:
            Path(args[2]).unlink(missing_ok=True);return SimpleNamespace(exit_code=0,result='')
        if args[:2]==['mkdir','-p']:
            Path(args[2]).mkdir(parents=True,exist_ok=True);return SimpleNamespace(exit_code=0,result='')
        result=subprocess.run([sys.executable,*args[1:]],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        return SimpleNamespace(exit_code=result.returncode,result=result.stdout)
    w=SimpleNamespace(project_id='recovery-project',sandbox=SimpleNamespace(process=SimpleNamespace(exec=execute),fs=SimpleNamespace(
        download_file=lambda name:Path(name).read_bytes(),upload_file=lambda data,name:Path(name).write_bytes(data))))
    return w,root


def test_saved_source_returns_after_sandbox_archives_are_lost(workspace):
    w,root=workspace;original=history.operate(w,'capture',label='Completed source')
    for file in (root.parent/'.genesys-version-history').iterdir():file.unlink()
    (root/'src/App.jsx').write_text('fresh starter')
    assert history.restore_after_sandbox_loss(w,created=False) is None
    assert (root/'src/App.jsx').read_text()=='fresh starter'
    result=history.restore_after_sandbox_loss(w,created=True)
    assert result['restored']==original['id'] and result['verified'] is False
    assert (root/'src/App.jsx').read_text()=='saved working source'
    assert (root/'.env').read_text()=='private runtime configuration'
    assert not (root.parent/'.genesys-source-recovery.json').exists()


def test_failed_recovery_pins_version_and_retries_without_overwriting_newer_existing_work(workspace,monkeypatch):
    w,root=workspace;original=history.operate(w,'capture',label='Completed source')
    (root/'src/App.jsx').write_text('fresh starter')
    actual=history.operate
    def fail(workspace,action,**payload):
        if action=='restore':
            actual(workspace,'capture',label='Starter backup before interrupted restore')
            raise RuntimeError('interrupted')
        return actual(workspace,action,**payload)
    monkeypatch.setattr(history,'operate',fail)
    with pytest.raises(RuntimeError,match='interrupted'):history.restore_after_sandbox_loss(w,created=True)
    marker=root.parent/'.genesys-source-recovery.json'
    assert json.loads(marker.read_bytes())['version']==original['id']
    monkeypatch.setattr(history,'operate',actual)
    history.restore_after_sandbox_loss(w,created=False)
    assert (root/'src/App.jsx').read_text()=='saved working source'
    (root/'src/App.jsx').write_text('later owner edit')
    assert history.restore_after_sandbox_loss(w,created=False) is None
    assert (root/'src/App.jsx').read_text()=='later owner edit'
