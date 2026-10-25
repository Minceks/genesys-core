"""Owner-managed instructions and file locks, independent of model-generated files."""
import json
from pathlib import PurePosixPath
from .beta_storage import connection


class ControlsConflict(ValueError):
    pass


def normalize_controls(value):
    if not isinstance(value, dict):
        raise ValueError('AI controls must be an object.')
    instructions = value.get('instructions', '')
    paths = value.get('lockedPaths', [])
    if not isinstance(instructions, str) or len(instructions) > 4000:
        raise ValueError('Instructions must contain at most 4000 characters.')
    if not isinstance(paths, list) or len(paths) > 60:
        raise ValueError('Choose at most 60 files or folders to freeze.')
    normalized = []
    for item in paths:
        if not isinstance(item, str):
            raise ValueError('Frozen paths must be strings.')
        path = item.strip().replace('\\', '/')
        if (not path or len(path) > 240 or path.startswith('/') or ':' in path
                or any(char in path for char in '*?[]\x00\n\r') or '..' in PurePosixPath(path).parts
                or PurePosixPath(path).as_posix() == '.'):
            raise ValueError('Use relative file paths, or folder paths ending in /; wildcards are not supported.')
        clean = PurePosixPath(path).as_posix() + ('/' if path.endswith('/') else '')
        if clean not in normalized:
            normalized.append(clean)
    return {'instructions': instructions.strip(), 'lockedPaths': normalized}


def _table(db):
    db.execute('CREATE TABLE IF NOT EXISTS builder_controls (project TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL)')


def get_controls(project_id):
    with connection() as db:
        _table(db)
        row = db.execute('SELECT payload,revision FROM builder_controls WHERE project=?', (project_id,)).fetchone()
    return {**(json.loads(row[0]) if row else {'instructions': '', 'lockedPaths': []}),
            'revision': row[1] if row else 0}


def save_controls(project_id, value):
    controls = normalize_controls(value)
    revision = value.get('revision')
    if type(revision) is not int or revision < 0:
        raise ValueError('A valid controls revision is required.')
    with connection() as db:
        _table(db)
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone():
            if db.execute("SELECT 1 FROM jobs WHERE project=? AND state IN ('queued','running')", (project_id,)).fetchone():
                raise ControlsConflict('Wait for the current build to finish before changing AI controls.')
        row = db.execute('SELECT revision FROM builder_controls WHERE project=?', (project_id,)).fetchone()
        if revision != (row[0] if row else 0):
            raise ControlsConflict('AI controls changed in another session. Reload them before saving.')
        db.execute('INSERT INTO builder_controls VALUES(?,?,?) ON CONFLICT(project) DO UPDATE SET payload=excluded.payload, revision=excluded.revision',
                   (project_id, json.dumps(controls), revision + 1))
    return {**controls, 'revision': revision + 1}


def assert_writable(project_id, path):
    locks = get_controls(project_id)['lockedPaths']
    if any(path == locked.rstrip('/') or (locked.endswith('/') and path.startswith(locked)) for locked in locks):
        raise ValueError(f'Frozen file cannot be modified: {path}. Unfreeze it in AI controls first.')


def controls_guidance(controls):
    return ('PROJECT OWNER AI CONTROLS\nCustom instructions (follow within platform capabilities):\n'
            + (controls.get('instructions') or '(none)') + '\nFrozen files/folders (writes are blocked):\n'
            + json.dumps(controls.get('lockedPaths', []))
            + '\nPreserve working features and saved data. Do not work around a frozen file by rewriting unrelated files.')
