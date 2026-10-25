import hashlib
import json

import pytest

from scripts.recover_completed_previews import recover
from agent import preview_hosting as hosting


def bundle(tmp_path, monkeypatch):
    monkeypatch.setenv('RAILWAY_VOLUME_MOUNT_PATH', str(tmp_path / 'volume'))
    monkeypatch.setenv('GENESYS_PREVIEW_PROXY_KEY', 'test-preview-recovery-' * 3)
    project = '65ee33d0-25a3-41f9-b589-4b933e1d5563'
    folder = tmp_path / 'bundle'
    (folder / 'files' / 'assets').mkdir(parents=True)
    data = {'index.html': b'<h1>Verified</h1>', 'assets/app.js': b'console.log("ready")'}
    for name, content in data.items():
        (folder / 'files' / name).write_bytes(content)
    manifest = {'projectId': project, 'proof': {'checkpointId': 'verified', 'commit': 'abc'},
                'files': {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}}
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    return folder, project, manifest


def test_recovery_survives_restart_and_never_overwrites_existing_or_disabled(tmp_path, monkeypatch):
    folder, project, _ = bundle(tmp_path, monkeypatch)
    assert recover(folder)
    ticket = hosting.ticket_for(project)
    active = hosting.directory(ticket)
    assert (active / 'assets/app.js').read_bytes() == b'console.log("ready")'
    assert not recover(folder)
    assert hosting.directory(ticket) == active
    (hosting.root() / ticket / '.disabled').touch()
    assert not recover(folder)
    assert hosting.directory(ticket) is None


@pytest.mark.parametrize('failure', ['checksum', 'traversal', 'size'])
def test_invalid_recovery_never_activates(tmp_path, monkeypatch, failure):
    folder, project, manifest = bundle(tmp_path, monkeypatch)
    if failure == 'checksum':
        (folder / 'files/index.html').write_text('tampered')
    elif failure == 'traversal':
        manifest['files']['../outside'] = 'bad'
        (folder / 'manifest.json').write_text(json.dumps(manifest))
    else:
        monkeypatch.setattr(hosting, 'MAX_BUILD', 1)
    with pytest.raises(ValueError):
        recover(folder)
    assert hosting.directory(hosting.ticket_for(project)) is None
