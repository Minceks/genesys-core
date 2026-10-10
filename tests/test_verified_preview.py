import shlex
from types import SimpleNamespace
from pathlib import Path

from agent.verified_preview import verified_preview


def test_snapshot_changes_only_when_published_and_keeps_old_assets(tmp_path, monkeypatch):
    from agent import daytona_workspace
    root = tmp_path / 'workspace' / 'project'
    dist = root / 'dist'
    (dist / 'assets').mkdir(parents=True)
    (dist / 'index.html').write_text('verified first')
    (dist / 'assets' / 'first.js').write_text('first bundle')
    monkeypatch.setattr(daytona_workspace, 'REMOTE_PROJECT_ROOT', str(root))
    def execute(command, **kwargs):
        if command.startswith('python3 -c '):
            exec(shlex.split(command)[2], {})
        return SimpleNamespace(exit_code=0, result='')
    sandbox = SimpleNamespace(
        process=SimpleNamespace(exec=execute),
        fs=SimpleNamespace(upload_file=lambda data, path: Path(path).write_bytes(data)),
        create_signed_preview_url=lambda *args, **kwargs: SimpleNamespace(url='https://4174-example.daytonaproxy01.eu'),
    )
    workspace = SimpleNamespace(sandbox=sandbox)
    proof = {'checkpointId': 'checkpoint', 'commit': 'abc'}
    verified_preview(workspace, proof)
    live = root.parent / '.genesys-verified-preview'
    assert (live / 'index.html').read_text() == 'verified first'
    (dist / 'index.html').write_text('in progress')
    verified_preview(workspace)
    assert (live / 'index.html').read_text() == 'verified first'
    (dist / 'assets' / 'second.js').write_text('second bundle')
    verified_preview(workspace, proof)
    assert (live / 'index.html').read_text() == 'in progress'
    assert (live / 'assets' / 'first.js').exists()
