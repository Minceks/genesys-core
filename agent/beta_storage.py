"""Shared persistent beta accounting and feedback storage."""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def connection():
    path = os.getenv('GENESYS_JOB_DB', str(Path(os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '.genesys-data')) / 'jobs.sqlite3'))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    try:
        with db:
            yield db
    finally:
        db.close()
