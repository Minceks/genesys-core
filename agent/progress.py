from contextvars import ContextVar
import os


progress_callback = ContextVar("genesys_progress_callback", default=None)


def execution_timeout(configured, background=False):
    if background:
        return min(900, max(60, int(os.getenv('GENESYS_BACKGROUND_TIMEOUT_SECONDS', '600'))))
    return min(configured, 240)


def report_progress(stage: str) -> None:
    callback = progress_callback.get()
    if callback is not None:
        callback(stage)
