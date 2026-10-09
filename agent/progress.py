from contextvars import ContextVar


progress_callback = ContextVar("genesys_progress_callback", default=None)


def report_progress(stage: str) -> None:
    callback = progress_callback.get()
    if callback is not None:
        callback(stage)
