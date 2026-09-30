from __future__ import annotations

import logging
import os


LOG_LEVEL = os.getenv(
    "GENESYS_LOG_LEVEL",
    "INFO",
).upper()


def configure_logging() -> None:
    """
    Configure application-wide structured logging.
    """

    logging.basicConfig(
        level=getattr(
            logging,
            LOG_LEVEL,
            logging.INFO,
        ),
        format=(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s"
        ),
    )


def get_logger(
    name: str,
) -> logging.Logger:
    """
    Return a logger for the requested module.
    """

    return logging.getLogger(name)