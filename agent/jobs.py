"""SQLite-backed jobs with renewable leases and bounded restart recovery."""
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .progress import progress_callback
from .logging_config import request_id_context

logger = logging.getLogger(__name__)

class JobManager:
    def __init__(self, workers=2, execute=None):
        self.workers = workers
        self.execute = execute
        self.owner = uuid.uuid4().hex
        if os.getenv("RAILWAY_ENVIRONMENT_ID") and not os.getenv("RAILWAY_VOLUME_MOUNT_PATH"):
            raise RuntimeError("Durable jobs require a mounted Railway volume")
        self.path = os.getenv("GENESYS_JOB_DB", str(Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".genesys-data")) / "jobs.sqlite3"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="genesys-job")
        self.active = set()
        self.lock = threading.Lock()
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, user_id TEXT,
                payload TEXT NOT NULL, history TEXT NOT NULL, reservation TEXT,
                state TEXT NOT NULL, owner TEXT, lease REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL)""")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS active_project ON jobs(project) WHERE state IN ('queued','running')")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS active_user ON jobs(user_id) WHERE state IN ('queued','running') AND user_id IS NOT NULL")
        if execute:
            threading.Thread(target=self.dispatch, daemon=True, name="genesys-queue").start()

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def submit(self, project_id, request_id, prompt="", history=None, reservation=None, user_id=None):
        job_id = uuid.uuid4().hex
        now = time.time()
        payload = {"jobId": job_id, "projectId": project_id, "prompt": prompt,
                   "createdAt": now * 1000, "requestId": request_id,
                   "state": "running", "stage": "Waiting for a worker", "restartCount": 0}
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM jobs WHERE state IN ('completed','failed') AND updated < ?", (now - 86400,))
            if db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0] >= 100:
                raise ValueError("GeneSys is busy. Please try again shortly.")
            try:
                db.execute("INSERT INTO jobs(id,project,user_id,payload,history,reservation,state,updated) VALUES(?,?,?,?,?,?,?,?)",
                    (job_id, project_id, user_id, json.dumps(payload), json.dumps(history or []), json.dumps(reservation), "queued", now))
            except sqlite3.IntegrityError:
                raise ValueError("A request is already running for this project or account.") from None
        return job_id

    def dispatch(self):
        while True:
            try:
                claimed = []
                with self.lock:
                    available = self.workers - len(self.active)
                    active = tuple(self.active)
                with self.connection() as db:
                    db.execute("BEGIN IMMEDIATE")
                    for job_id in active:
                        db.execute("UPDATE jobs SET lease=? WHERE id=? AND owner=? AND state='running'", (time.time() + 90, job_id, self.owner))
                    if available > 0:
                        rows = db.execute("SELECT id,payload,history,reservation,attempts FROM jobs WHERE state='queued' OR (state='running' AND lease<?) ORDER BY updated LIMIT ?", (time.time(), available)).fetchall()
                        for job_id, raw, history, reservation, attempts in rows:
                            payload = json.loads(raw)
                            if attempts >= 3:
                                payload.update(state="failed", stage="Request interrupted", result={"status":"error", "message":"This request was interrupted repeatedly. Your project files are preserved; please retry."})
                                db.execute("UPDATE jobs SET state='failed',payload=?,updated=? WHERE id=?", (json.dumps(payload), time.time(), job_id))
                                continue
                            payload['restartCount'] = attempts
                            if attempts:
                                payload['previousStage'] = payload['stage']
                                payload['stage'] = "Resuming saved project after service restart"
                            db.execute("UPDATE jobs SET state='running',owner=?,lease=?,attempts=attempts+1,payload=? WHERE id=?", (self.owner, time.time()+90, json.dumps(payload), job_id))
                            claimed.append((payload, json.loads(history), json.loads(reservation), attempts))
                for args in claimed:
                    with self.lock:
                        self.active.add(args[0]['jobId'])
                    self.executor.submit(self.run, *args)
            except Exception:
                logger.exception("durable_job_dispatch_failed")
            time.sleep(5)

    def update(self, job_id, **changes):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM jobs WHERE id=? AND owner=?", (job_id, self.owner)).fetchone()
            if not row:
                raise RuntimeError("Job lease ownership was lost")
            payload = json.loads(row[0])
            payload.update(changes)
            db.execute("UPDATE jobs SET payload=?,state=?,updated=? WHERE id=? AND owner=?", (json.dumps(payload), payload['state'], time.time(), job_id, self.owner))

    def run(self, job, history, reservation, attempts):
        job_id = job['jobId']
        progress_token = progress_callback.set(lambda stage: self.update(job_id, stage=stage))
        request_token = request_id_context.set(job['requestId'])
        try:
            recovery = None
            if attempts:
                recovery = ("This accepted request was interrupted by a service restart. "
                    "The original request is unchanged. Existing Daytona files contain partial work. "
                    "Before editing, read the relevant existing user project files and compare them "
                    "with the original request and conversation. Make a brief requirements checklist: "
                    "what the user asked for, what is already implemented, and what is missing or broken. "
                    "Base completion claims on file contents and verification, never on the saved stage alone. "
                    "Preserve completed features, design, dependencies, and user data. Do not recreate the "
                    "project, replace working files wholesale, duplicate components, or apply an edit twice. "
                    "Implement only missing requirements or necessary repairs. If the requested work is "
                    "already implemented, finish implementation without edits so mandatory build and "
                    "browser verification can run again. Report what was retained, completed, and verified. "
                    "Last recorded stage (informational, not proof of completion): " + job.get('previousStage', 'unknown'))
            result = self.execute(job['prompt'], job['projectId'], history, reservation, recovery)
            state = 'completed' if result.get('status') == 'success' else 'failed'
            self.update(job_id, state=state, stage='Complete' if state == 'completed' else 'Request failed', result=result)
        except Exception:
            logger.exception("background_agent_failed")
            try:
                self.update(job_id, state='failed', stage='Request failed', result={"status":"error", "message":"The request failed. Your project files are preserved; please retry."})
            except Exception:
                logger.exception("durable_job_result_save_failed")
        finally:
            progress_callback.reset(progress_token)
            request_id_context.reset(request_token)
            with self.lock:
                self.active.discard(job_id)

    def get(self, job_id, project_id):
        with self.connection() as db:
            row = db.execute("SELECT payload FROM jobs WHERE id=? AND project=?", (job_id, project_id)).fetchone()
            return json.loads(row[0]) if row else None

    def latest(self, project_id):
        with self.connection() as db:
            row = db.execute("SELECT payload FROM jobs WHERE project=? ORDER BY rowid DESC LIMIT 1", (project_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def is_running(self, project_id):
        with self.connection() as db:
            return bool(db.execute("SELECT 1 FROM jobs WHERE project=? AND state IN ('queued','running')", (project_id,)).fetchone())
