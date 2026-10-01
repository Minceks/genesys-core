from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar


request_id_context: ContextVar[str] = ContextVar(
    "genesys_request_id",
    default="-",
)


class RequestIdFilter(logging.Filter):
    """Attach the current HTTP request ID to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def configure_logging() -> None:
    """
    Configure application-wide structured logging.
    """

    root_logger = logging.getLogger()
    log_level = os.getenv("GENESYS_LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(
        getattr(logging, log_level, logging.INFO)
    )

    log_format = (
        "%(asctime)s %(levelname)s %(name)s "
        "request_id=%(request_id)s %(message)s"
    )

    if not root_logger.handlers:
        logging.basicConfig(
            stream=sys.stdout,
            format=log_format,
        )

    for handler in root_logger.handlers:
        handler.setFormatter(logging.Formatter(log_format))
        if not any(
            isinstance(item, RequestIdFilter)
            for item in handler.filters
        ):
            handler.addFilter(RequestIdFilter())


def get_logger(
    name: str,
) -> logging.Logger:
    """
    Return a logger for the requested module.
    """

    return logging.getLogger(name)
