"""Persist an immutable verified static build independently of Daytona."""
import io
import json
import os
import re
from pathlib import Path, PurePosixPath
import shlex
import shutil
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
    from .beta_storage import connection
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS project_publications(project_id TEXT PRIMARY KEY, publication TEXT UNIQUE NOT NULL)')
        db.execute('INSERT OR IGNORE INTO project_publications VALUES(?,?)', (project_id, uuid.uuid4().hex))
        publication = db.execute('SELECT publication FROM project_publications WHERE project_id=?', (project_id,)).fetchone()[0]
    revision = uuid.uuid4().hex
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
    current = workspace.sandbox.process.exec(
        'cat ../.genesys-verified-preview/.proof.json', cwd=REMOTE_PROJECT_ROOT, timeout=10)
    if current.exit_code != 0 or json.loads(current.result) != {'checkpointId': checkpoint_id, 'commit': commit}:
        raise ValueError('The verified build changed during export. Review the latest version before publishing.')
    if len(blob) > 25 * 1024 * 1024:
        raise ValueError('The published build exceeds the 25 MB beta limit.')
    base = root() / publication
    destination = base / ".versions" / revision
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
    active = base / '.active'
    if active.is_file():
        previous = active.read_text().strip()
        if re.fullmatch(r'[0-9a-f]{32}', previous):
            assets = base / '.versions' / previous / 'assets'
            if assets.is_dir():
                shutil.copytree(assets, destination / 'assets', dirs_exist_ok=True)
    # Vite's default root-relative hashed assets need the publication prefix.
    index = destination / 'index.html'
    content = index.read_text(encoding='utf-8')
    content = content.replace('"/assets/', f'"/apps/{publication}/assets/').replace("'/assets/", f"'/apps/{publication}/assets/")
    index.write_text(content, encoding='utf-8')
    (base / '.publication.json').write_text(json.dumps({
        'projectId': project_id, 'checkpointId': checkpoint_id, 'commit': commit
    }), encoding='utf-8')
    pointer = base / ('.active-' + revision)
    pointer.write_text(revision, encoding='ascii')
    os.replace(pointer, base / '.active')
    (base / '.unpublished').unlink(missing_ok=True)
    return publication
