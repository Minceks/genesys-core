import json
from pathlib import Path
import zipfile
import pytest
from agent.version_worker import capture,restore,versions,eligible


def test_history_restores_source_and_retains_current_work_without_touching_secrets(tmp_path):
    root=tmp_path/'project';(root/'src').mkdir(parents=True)
    store=tmp_path/'history'
    (root/'src/App.jsx').write_text('original')
    (root/'.env').write_text('PRIVATE')
    (root/'src/secrets.json').write_text('PRIVATE')
    (root/'dist').mkdir();(root/'dist/index.html').write_text('published')
    old=capture(root,store,'Before build')
    (root/'src/App.jsx').write_text('changed')
    (root/'src/Extra.jsx').write_text('new')
    result=restore(root,store,old['id'])
    assert (root/'src/App.jsx').read_text()=='original'
    assert not (root/'src/Extra.jsx').exists()
    assert (root/'.env').read_text()=='PRIVATE'
    assert (root/'dist/index.html').read_text()=='published'
    assert result['verified'] is False
    with zipfile.ZipFile(store/(result['backup']+'.zip')) as archive:
        assert archive.read('src/App.jsx')==b'changed'
        assert '.env' not in archive.namelist() and 'src/secrets.json' not in archive.namelist()


def test_bad_hash_and_frozen_paths_block_restore_before_mutation(tmp_path):
    root=tmp_path/'project';(root/'src').mkdir(parents=True);store=tmp_path/'history'
    (root/'src/App.jsx').write_text('before');old=capture(root,store,'first')
    (root/'src/App.jsx').write_text('now')
    with pytest.raises(ValueError,match='Unfreeze'):restore(root,store,old['id'],['src/'])
    with zipfile.ZipFile(store/(old['id']+'.zip'),'w') as archive:archive.writestr('src/App.jsx','tampered')
    with pytest.raises(ValueError,match='integrity'):restore(root,store,old['id'])
    assert (root/'src/App.jsx').read_text()=='now'


def test_history_rejects_traversal_symlinks_and_bounds_versions(tmp_path):
    assert not eligible('../secret.js') and not eligible('src/.env.js')
    root=tmp_path/'project';root.mkdir();store=tmp_path/'history'
    (root/'index.html').write_text('site')
    for n in range(32):capture(root,store,str(n))
    assert len(versions(store))==30
    with pytest.raises(ValueError):restore(root,store,'../escape')


def test_durable_history_survives_loss_of_remote_archives(tmp_path,monkeypatch):
    import shlex
    import subprocess
    import sys
    from types import SimpleNamespace
    from agent import daytona_workspace,version_history
    root=tmp_path/'sandbox/project';(root/'src').mkdir(parents=True)
    (root/'src/App.jsx').write_text('original')
    monkeypatch.setattr(daytona_workspace,'REMOTE_PROJECT_ROOT',str(root))
    monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH',str(tmp_path/'volume'))
    def execute(command,**kwargs):
        args=shlex.split(command)
        if args[:2]==['mkdir','-p']:
            Path(args[2]).mkdir(parents=True,exist_ok=True)
            return SimpleNamespace(exit_code=0,result='')
        result=subprocess.run([sys.executable,*args[1:]],capture_output=True,text=True)
        assert result.returncode==0,result.stderr
        return SimpleNamespace(exit_code=result.returncode,result=result.stdout)
    workspace=SimpleNamespace(project_id='durable-project',sandbox=SimpleNamespace(
        process=SimpleNamespace(exec=execute),fs=SimpleNamespace(
            download_file=lambda path:Path(path).read_bytes(),
            upload_file=lambda data,path:Path(path).write_bytes(data))))
    original=version_history.operate(workspace,'capture',label='Original')
    remote=root.parent/'.genesys-version-history'
    for file in remote.iterdir():file.unlink()
    (root/'src/App.jsx').write_text('new work')
    assert version_history.local_versions(workspace.project_id)[0]['id']==original['id']
    result=version_history.operate(workspace,'restore',id=original['id'])
    assert (root/'src/App.jsx').read_text()=='original'
    local=version_history.storage(workspace.project_id)
    with zipfile.ZipFile(local/(result['backup']+'.zip')) as archive:
        assert archive.read('src/App.jsx')==b'new work'
