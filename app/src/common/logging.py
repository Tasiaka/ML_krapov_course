from __future__ import annotations

import logging
import os
import sys
from typing import Any


def setup_logging(service_name: str) -> None:
    """Basic structured logging to stdout.

    - Works well in Docker (stdout/stderr)
    - Controlled via LOG_LEVEL env (default: INFO)
    """
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)


    root = logging.getLogger()
    if getattr(root, "_configured_by_project", False):
        return

    fmt = (
        "%(asctime)s | %(levelname)s | %(name)s | service=%(service)s "
        "| %(message)s"
    )

    class _ServiceFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            setattr(record, "service", service_name)
            return True

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    handler.addFilter(_ServiceFilter())

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    setattr(root, "_configured_by_project", True)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("pika").setLevel(logging.WARNING)
