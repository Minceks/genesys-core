from contextvars import ContextVar
from contextlib import contextmanager
import os
import time


progress_callback = ContextVar("genesys_progress_callback", default=None)
model_deadline = ContextVar('genesys_model_deadline', default=None)
REVIEW_RESERVE_SECONDS = 180


class ModelDeadlineExceeded(RuntimeError):
    pass


@contextmanager
def model_request_scope(deadline):
    parent = model_deadline.get()
    token = model_deadline.set(min(parent, deadline) if parent is not None else deadline)
    try: yield
    finally: model_deadline.reset(token)


def model_request_timeout(default):
    deadline = model_deadline.get()
    if deadline is None: return float(default)
    remaining = deadline - time.monotonic()
    if remaining <= 1:
        raise ModelDeadlineExceeded('The model request time budget ended; saved project files are preserved.')
    return min(float(default), remaining)


def execution_timeout(configured, background=False):
    if background:
        return min(900, max(60, int(os.getenv('GENESYS_BACKGROUND_TIMEOUT_SECONDS', '900'))))
    return min(configured, 240)


def report_progress(stage: str) -> None:
    callback = progress_callback.get()
    if callback is not None:
        callback(stage)


def draft_stage_deadline(deadline):
    """Initial drafts cannot spend the compilation, repair and review reserve."""
    now = time.monotonic()
    reserve = min(300, max(120, (deadline-now)*.4))
    return min(now+420, deadline-reserve)
