"""Persist an immutable verified static build independently of Daytona."""
import io
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import tarfile
import uuid


def root():
    return Path(os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '.genesys-data')) / 'published'


def publish(workspace, project_id, checkpoint_id, commit):
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    workspace._ensure_sandbox_running()
    if sum(path.stat().st_size for path in root().rglob('*') if path.is_file()) > 200 * 1024 * 1024:
        raise ValueError('Beta publishing storage is full. Contact the GeneSys administrator.')
    proof = workspace.sandbox.process.exec(
        'cat ../.genesys-verified-preview/.proof.json', cwd=REMOTE_PROJECT_ROOT, timeout=10)
    if proof.exit_code != 0 or json.loads(proof.result) != {'checkpointId': checkpoint_id, 'commit': commit}:
        raise ValueError('Rebuild and verify this version before publishing.')
    publication = uuid.uuid4().hex
    archive = '/tmp/genesys-publish-' + publication + '.tar'
    result = workspace.sandbox.process.exec(
        'tar -cf ' + shlex.quote(archive) + ' --exclude=.proof.json -C ../.genesys-verified-preview .',
        cwd=REMOTE_PROJECT_ROOT, timeout=30)
    if result.exit_code != 0:
        raise ValueError('Could not export the verified build.')
    try:
        blob = workspace.sandbox.fs.download_file(archive)
    finally:
        workspace.sandbox.process.exec('rm -f ' + shlex.quote(archive), timeout=10)
    if len(blob) > 25 * 1024 * 1024:
        raise ValueError('The published build exceeds the 25 MB beta limit.')
    destination = root() / publication
    total = 0
    with tarfile.open(fileobj=io.BytesIO(blob)) as bundle:
        members = bundle.getmembers()
        if len(members) > 2000:
            raise ValueError('The build contains too many files.')
        for member in members:
            path = PurePosixPath(member.name)
            total += member.size
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()) or total > 25 * 1024 * 1024:
                raise ValueError('The build contains unsupported files.')
        if not any(PurePosixPath(m.name).as_posix().lstrip('./') == 'index.html' for m in members):
            raise ValueError('The build has no index.html.')
        destination.mkdir(parents=True)
        bundle.extractall(destination, filter='data')
    # Vite's default root-relative hashed assets need the publication prefix.
    index = destination / 'index.html'
    content = index.read_text(encoding='utf-8')
    content = content.replace('"/assets/', f'"/apps/{publication}/assets/').replace("'/assets/", f"'/apps/{publication}/assets/")
    index.write_text(content, encoding='utf-8')
    (destination / '.publication.json').write_text(json.dumps({
        'projectId': project_id, 'checkpointId': checkpoint_id, 'commit': commit
    }), encoding='utf-8')
    return publication
