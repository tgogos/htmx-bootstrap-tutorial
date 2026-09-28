"""Stdlib logging: stdout only, text in development, JSON in production."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_HANDLER_MARK = "_fastapi_htmx_bootstrap"
_RESERVED_RECORD_KEYS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "asctime",
        "taskName",
    }
)

_TEXT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
_TEXT_DATEFMT = "%Y-%m-%dT%H:%M:%S"

# Driver/client libraries spam DEBUG (e.g. pymongo topology heartbeats).
_LIBRARY_LOGGERS = (
    "pymongo",
    "motor",
    "httpx",
    "httpcore",
    "urllib3",
)


class JsonFormatter(logging.Formatter):
    """One JSON object per line for log shippers."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def use_json_logs(environment: str) -> bool:
    return environment.strip().lower() == "production"


def setup_logging() -> None:
    """Configure root + uvicorn loggers. Safe to call more than once."""
    from app.core import config

    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    formatter: logging.Formatter
    if use_json_logs(config.ENVIRONMENT):
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(fmt=_TEXT_FORMAT, datefmt=_TEXT_DATEFMT)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    setattr(handler, _HANDLER_MARK, True)

    root = logging.getLogger()
    # Libraries inherit this. Do not put DEBUG on root or pymongo heartbeats
    # flood stdout when LOG_LEVEL=DEBUG.
    root.setLevel(logging.INFO)
    _replace_stream_handlers(root, handler)

    logging.getLogger("app").setLevel(level)

    for name in _LIBRARY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    for name in ("uvicorn", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.setLevel(level)
        uv.handlers.clear()
        uv.propagate = True

    # Access logs stay on even when LOG_LEVEL is WARNING.
    access = logging.getLogger("uvicorn.access")
    access.setLevel(logging.INFO)
    access.handlers.clear()
    access.addHandler(handler)
    access.propagate = False


def _replace_stream_handlers(
    logger: logging.Logger, handler: logging.Handler
) -> None:
    """Swap stdout handlers; keep pytest caplog (not a StreamHandler)."""
    for existing in list(logger.handlers):
        if getattr(existing, _HANDLER_MARK, False) or type(existing) is logging.StreamHandler:
            logger.removeHandler(existing)
    logger.addHandler(handler)
