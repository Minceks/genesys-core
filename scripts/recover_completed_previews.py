"""Restore explicitly packaged, hash-checked public builds when hosting is missing.

This is an operator recovery path, not a way to mark new agent output verified.
Existing previews (including disabled previews) are never replaced.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import uuid

from agent import preview_hosting as hosting


def recover(bundle):
    bundle = Path(bundle)
    manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
    project = manifest['projectId']
    if not isinstance(project, str) or not re.fullmatch(r'[0-9a-f-]{36}', project):
        raise ValueError('Invalid recovery project')
    proof = manifest['proof']
    if not isinstance(proof, dict) or not all(isinstance(proof.get(k), str) and proof[k] for k in ('checkpointId', 'commit')):
        raise ValueError('Missing recovery proof')
    base = hosting.root() / hosting.ticket_for(project)
    if (base / '.active').exists() or (base / '.disabled').exists():
        return False
    files = manifest['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= 2000 or 'index.html' not in files:
        raise ValueError('Invalid recovery file list')
    contents = {}
    for name, digest in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '\\' in name or any(p.startswith('.') for p in path.parts)
                or (bundle / 'files' / name).is_symlink()):
            raise ValueError('Unsafe recovery path')
        source = bundle / 'files' / name
        if not source.resolve().is_relative_to((bundle / 'files').resolve()):
            raise ValueError('Unsafe recovery path')
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('Recovery checksum mismatch')
        contents[name] = content
    total = sum(map(len, contents.values()))
    used = sum(p.stat().st_size for p in hosting.root().rglob('*') if p.is_file())
    if total > hosting.MAX_BUILD or used + total > hosting.MAX_STORAGE:
        raise ValueError('Recovery exceeds hosting limits')
    revision = uuid.uuid4().hex
    destination = base / '.versions' / revision
    try:
        for name, content in contents.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (destination / '.proof.json').write_text(json.dumps(proof), encoding='utf-8')
        pointer = base / ('.active-' + revision)
        pointer.write_text(revision, encoding='ascii')
        # Only startup recovery uses this path; do not replace a saved build.
        if (base / '.active').exists() or (base / '.disabled').exists():
            pointer.unlink()
            shutil.rmtree(destination)
            return False
        os.replace(pointer, base / '.active')
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return True


def main():
    bundles = Path(__file__).resolve().parents[1] / 'preview_recovery'
    if not bundles.is_dir():
        return
    import logging
    for manifest in bundles.glob('*/manifest.json'):
        try:
            restored = recover(manifest.parent)
            logging.getLogger(__name__).info('completed_preview_recovery restored=%s', restored)
        except Exception:
            logging.getLogger(__name__).exception('completed_preview_recovery_failed')
