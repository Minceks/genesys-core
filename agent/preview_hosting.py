"""Durable completed previews, served on isolated project origins."""
import hashlib
import hmac
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import tarfile
import uuid

MAX_BUILD = 25 * 1024 * 1024
MAX_STORAGE = 200 * 1024 * 1024


def configured():
    return bool(os.getenv('GENESYS_PREVIEW_DOMAIN', '').strip()) and len(os.getenv('GENESYS_PREVIEW_PROXY_KEY', '')) >= 32


def root():
    mount = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
    if os.getenv('RAILWAY_ENVIRONMENT_ID') and not mount:
        raise RuntimeError('Persistent preview storage requires a mounted volume.')
    return Path(mount or '.genesys-data') / 'completed-previews'


def ticket_for(project_id):
    secret = os.getenv('GENESYS_PREVIEW_PROXY_KEY', '')
    if len(secret) < 32 or not project_id or len(project_id) > 128:
        raise ValueError('Persistent preview configuration is incomplete.')
    return hmac.new(secret.encode(), ('project:' + project_id).encode(), hashlib.sha256).hexdigest()[:32]


def directory(ticket):
    if not re.fullmatch(r'[0-9a-f]{32}', ticket):
        return None
    base = root() / ticket
    if (base / '.disabled').exists() or not (base / '.active').is_file():
        return None
    revision = (base / '.active').read_text().strip()
    if not re.fullmatch(r'[0-9a-f]{32}', revision):
        return None
    active = base / '.versions' / revision
    return active if (active / 'index.html').is_file() else None


def available_url(project_id):
    domain = os.getenv('GENESYS_PREVIEW_DOMAIN', '').strip().lower()
    if not configured():
        return None
    ticket = ticket_for(project_id)
    return f'https://{ticket}.{domain}/' if directory(ticket) else None


def save(workspace, project_id):
    """Export only the immutable verified snapshot, never a working dist folder."""
    from .daytona_workspace import REMOTE_PROJECT_ROOT
    ticket = ticket_for(project_id)
    domain = os.getenv('GENESYS_PREVIEW_DOMAIN', '').strip().lower()
    if not domain:
        raise ValueError('A preview domain is required.')
    workspace._ensure_sandbox_running()
    def read_proof():
        result = workspace.sandbox.process.exec('cat ../.genesys-verified-preview/.proof.json', cwd=REMOTE_PROJECT_ROOT, timeout=10)
        if result.exit_code != 0:
            raise ValueError('No verified build is available to preserve.')
        proof = json.loads(result.result)
        if not isinstance(proof, dict) or not all(isinstance(proof.get(k), str) and proof[k] for k in ('checkpointId', 'commit')):
            raise ValueError('The verified build proof is invalid.')
        return proof
    proof = read_proof()
    old = directory(ticket)
    if old and json.loads((old / '.proof.json').read_text()) == proof:
        return f'https://{ticket}.{domain}/'
    revision = uuid.uuid4().hex
    archive = '/tmp/genesys-preview-' + revision + '.tar'
    try:
        result = workspace.sandbox.process.exec('tar -cf ' + shlex.quote(archive)
            + ' --exclude=.proof.json -C ../.genesys-verified-preview .', cwd=REMOTE_PROJECT_ROOT, timeout=30)
        if result.exit_code != 0:
            raise ValueError('Could not export the completed preview.')
        size = workspace.sandbox.process.exec('stat -c %s ' + shlex.quote(archive), timeout=10)
        if size.exit_code != 0 or int(size.result.strip()) > MAX_BUILD:
            raise ValueError('Completed preview exceeds the 25 MB hosting limit.')
        blob = workspace.sandbox.fs.download_file(archive)
        if read_proof() != proof:
            raise ValueError('The verified build changed during export; retry saving it.')
    finally:
        workspace.sandbox.process.exec('rm -f ' + shlex.quote(archive), timeout=10)
    base = root() / ticket
    destination = base / '.versions' / revision
    try:
        with tarfile.open(fileobj=io.BytesIO(blob)) as bundle:
            members = bundle.getmembers()
            total = sum(m.size for m in members)
            if len(members) > 2000 or total > MAX_BUILD:
                raise ValueError('Completed preview exceeds hosting limits.')
            for member in members:
                path = PurePosixPath(member.name)
                if (path.is_absolute() or '..' in path.parts or '\\' in member.name
                        or any(p.startswith('.') for p in path.parts if p != '.')
                        or not (member.isfile() or member.isdir())):
                    raise ValueError('Completed preview contains unsupported files.')
            if not any(PurePosixPath(m.name).as_posix() == 'index.html' and m.isfile() for m in members):
                raise ValueError('Completed preview has no index.html.')
            used = sum(p.stat().st_size for p in root().rglob('*') if p.is_file())
            if used + total > MAX_STORAGE:
                raise ValueError('Persistent preview storage is full.')
            destination.mkdir(parents=True)
            bundle.extractall(destination, filter='data')
        # Open tabs may still request an earlier hashed JS chunk after an update.
        if old and (old / 'assets').is_dir():
            shutil.copytree(old / 'assets', destination / 'assets', dirs_exist_ok=True)
        if sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()) > MAX_BUILD:
            raise ValueError('Completed preview assets exceed the hosting limit.')
        if sum(p.stat().st_size for p in root().rglob('*') if p.is_file()) > MAX_STORAGE:
            raise ValueError('Persistent preview storage is full.')
        (destination / '.proof.json').write_text(json.dumps(proof), encoding='utf-8')
        pointer = base / ('.active-' + revision)
        pointer.write_text(revision, encoding='ascii')
        os.replace(pointer, base / '.active')
        (base / '.disabled').unlink(missing_ok=True)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    # Retain the preceding revision as well as current; never expire for inactivity.
    keep = {destination.name, old.name if old else ''}
    for previous in (base / '.versions').iterdir():
        if previous.name not in keep:
            shutil.rmtree(previous)
    return f'https://{ticket}.{domain}/'


def disable(project_id):
    if not configured():
        return
    base = root() / ticket_for(project_id)
    if base.is_dir():
        (base / '.disabled').touch()


def start_migration():
    if not configured():
        return
    from scripts.recover_completed_previews import main as recover_packaged_previews
    recover_packaged_previews()
    refresh = [value.strip() for value in os.getenv('GENESYS_REFRESH_COMPLETED_PROJECTS', '').split(',') if value.strip()]
    if not refresh and os.getenv('GENESYS_MIGRATE_COMPLETED_PREVIEWS') != '1':
        return
    if not refresh and (root().parent / 'preview-migration-v1.json').exists():
        return
    if any(not re.fullmatch(r'[0-9a-fA-F-]{36}', value) for value in refresh):
        raise ValueError('Invalid completed-preview refresh project identifier.')
    import logging
    import threading
    def run():
        try:
            from scripts.migrate_completed_previews import main
            main(projects=refresh or None, refresh=bool(refresh))
        except Exception:
            logging.getLogger(__name__).exception('completed_preview_migration_failed')
    threading.Thread(target=run, name='completed-preview-migration', daemon=True).start()
