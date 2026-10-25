"""Retained desktop/phone screenshots and objective review findings."""
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from .beta_storage import connection


def root_dir():
    return Path(os.getenv('GENESYS_VISUAL_EVIDENCE_DIR', str(Path(os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '.genesys-data')) / 'visual-evidence')))


def _table(db):
    db.execute('CREATE TABLE IF NOT EXISTS visual_reviews(id TEXT PRIMARY KEY, project TEXT NOT NULL, created REAL NOT NULL, payload TEXT NOT NULL)')


def save_review(project, quality, captures):
    review_id = uuid.uuid4().hex
    directory = root_dir() / hashlib.sha256(project.encode()).hexdigest() / review_id
    directory.mkdir(parents=True, exist_ok=True)
    images = []
    for name, data in captures.items():
        if name not in {'desktop', 'phone'}:
            raise ValueError('Unknown review viewport')
        (directory / (name + '.png')).write_bytes(data)
        images.append({'viewport': name, 'sha256': hashlib.sha256(data).hexdigest()})
    record = {'id': review_id, 'createdAt': int(time.time() * 1000), 'status': quality['status'],
              'issues': quality.get('issues', []), 'suggestions': quality.get('suggestions', []),
              'snapshots': quality['snapshots'], 'images': images,
              'kind': quality.get('kind','generated'),
              'scope': quality.get('scope','Rendered layout and usability evidence; visual taste still requires review.')}
    if quality.get('kind') == 'reference':
        record['reference'] = quality.get('reference', {})
    if quality.get('referenceComparison'):
        record['referenceComparison'] = quality['referenceComparison']
    if quality.get('visualReview'):
        record['visualReview'] = quality['visualReview']
    with connection() as db:
        _table(db)
        db.execute('INSERT INTO visual_reviews VALUES(?,?,?,?)', (review_id, project, time.time(), json.dumps(record)))
        old = db.execute('SELECT id FROM visual_reviews WHERE project=? ORDER BY created DESC LIMIT -1 OFFSET 10', (project,)).fetchall()
        for (old_id,) in old:
            db.execute('DELETE FROM visual_reviews WHERE id=? AND project=?', (old_id, project))
            old_dir = directory.parent / old_id
            for filename in ('desktop.png', 'phone.png'):
                (old_dir / filename).unlink(missing_ok=True)
            if old_dir.exists():
                old_dir.rmdir()
    return record


def latest_reviews(project):
    with connection() as db:
        _table(db)
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM visual_reviews WHERE project=? ORDER BY created DESC LIMIT 10', (project,))]


def image_path(project, review_id, viewport):
    if viewport not in {'desktop', 'phone'} or not any(review['id'] == review_id for review in latest_reviews(project)):
        return None
    path = root_dir() / hashlib.sha256(project.encode()).hexdigest() / review_id / (viewport + '.png')
    return path if path.is_file() else None
