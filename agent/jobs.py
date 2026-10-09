"""Bounded beta jobs. State is process-local and expires after one hour."""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from .progress import progress_callback
from .logging_config import request_id_context


class JobManager:
    def __init__(self, workers=2):
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="genesys-job")
        self.workers = workers
        self.lock = threading.Lock()
        self.jobs = {}

    def submit(self, project_id, request_id, execute):
        with self.lock:
            now = time.monotonic()
            self.jobs = {key: job for key, job in self.jobs.items()
                         if job["state"] == "running" or now - job["updated"] < 3600}
            active = [job for job in self.jobs.values() if job["state"] == "running"]
            if any(job["projectId"] == project_id for job in active):
                raise ValueError("A request is already running for this project.")
            if len(active) >= self.workers or len(self.jobs) >= 100:
                raise ValueError("GeneSys is busy. Please try again shortly.")
            job_id = uuid.uuid4().hex
            self.jobs[job_id] = {"jobId": job_id, "projectId": project_id,
                "requestId": request_id, "state": "running", "stage": "Preparing request",
                "updated": now}

        def update(stage):
            with self.lock:
                self.jobs[job_id].update(stage=stage, updated=time.monotonic())

        def run():
            progress_token = progress_callback.set(update)
            request_token = request_id_context.set(request_id)
            try:
                result = execute()
                state = "completed" if result.get("status") == "success" else "failed"
                with self.lock:
                    self.jobs[job_id].update(state=state, stage="Complete" if state == "completed" else "Request failed",
                        result=result, updated=time.monotonic())
            except Exception:
                import logging
                logging.getLogger(__name__).exception("background_agent_failed")
                with self.lock:
                    self.jobs[job_id].update(state="failed", stage="Request failed",
                        result={"status": "error", "message": "The request failed. Please retry or report this problem."},
                        updated=time.monotonic())
            finally:
                progress_callback.reset(progress_token)
                request_id_context.reset(request_token)
        self.executor.submit(run)
        return job_id

    def get(self, job_id, project_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job["projectId"] != project_id or time.monotonic() - job["updated"] >= 3600:
                return None
            return {key: value for key, value in job.items() if key != "updated"}

    def is_running(self, project_id):
        with self.lock:
            return any(job["projectId"] == project_id and job["state"] == "running"
                       for job in self.jobs.values())
