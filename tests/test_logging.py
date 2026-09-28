"""Logging setup: formatters and LOG_LEVEL."""

import json
import logging

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import JsonFormatter, setup_logging, use_json_logs

pytestmark = pytest.mark.no_client


def _record(message: str = "hello", level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord(
        name="app.core.logging",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_json_formatter_emits_one_object():
    payload = json.loads(JsonFormatter().format(_record("hello")))
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.core.logging"
    assert "time" in payload


def test_json_formatter_includes_exception():
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys

        record = _record("failed")
        record.exc_info = sys.exc_info()
    text = JsonFormatter().format(record)
    payload = json.loads(text)
    assert "RuntimeError: boom" in payload["exception"]


def test_log_level_normalizes_and_rejects_unknown():
    assert Settings(LOG_LEVEL="debug").LOG_LEVEL == "DEBUG"
    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="verbose")


def test_use_json_logs_only_in_production():
    assert use_json_logs("production") is True
    assert use_json_logs("PRODUCTION") is True
    assert use_json_logs("development") is False
    assert use_json_logs("staging") is False


def test_setup_logging_text_in_development(capsys, monkeypatch):
    monkeypatch.setattr("app.core.config.ENVIRONMENT", "development")
    monkeypatch.setattr("app.core.config.LOG_LEVEL", "INFO")
    setup_logging()
    logging.getLogger("app.test").info("ping")
    out = capsys.readouterr().out
    assert "ping" in out
    assert "INFO" in out
    assert not out.lstrip().startswith("{")


def test_setup_logging_json_in_production(capsys, monkeypatch):
    monkeypatch.setattr("app.core.config.ENVIRONMENT", "production")
    monkeypatch.setattr("app.core.config.LOG_LEVEL", "INFO")
    setup_logging()
    logging.getLogger("app.test").warning("ship-me")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["message"] == "ship-me"
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "app.test"


def test_setup_logging_debug_does_not_enable_pymongo(monkeypatch):
    monkeypatch.setattr("app.core.config.ENVIRONMENT", "development")
    monkeypatch.setattr("app.core.config.LOG_LEVEL", "DEBUG")
    setup_logging()
    assert logging.getLogger("app").isEnabledFor(logging.DEBUG)
    assert logging.getLogger("app.utils.mongo").isEnabledFor(logging.DEBUG)
    assert not logging.getLogger("pymongo").isEnabledFor(logging.DEBUG)
    assert not logging.getLogger("pymongo.topology").isEnabledFor(logging.DEBUG)
