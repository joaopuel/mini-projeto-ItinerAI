"""Testes de `itinerai_agent/utils/logging_config.py` (T04/#15) — formatter JSON,
filtro de run_id e bootstrap idempotente."""

import json
import logging
import sys
import uuid

from itinerai_agent.utils import logging_config as LC


def _record(name="itinerai_agent.x", level=logging.INFO, msg="node_start", exc_info=None):
    return logging.LogRecord(name, level, "p", 1, msg, (), exc_info)


def test_new_run_id_is_uuid():
    rid = LC.new_run_id()
    uuid.UUID(rid)  # não levanta
    assert isinstance(rid, str)
    assert LC.new_run_id() != rid


def test_json_formatter_basic():
    rec = _record()
    rec.node = "validate_input"
    payload = json.loads(LC.JsonFormatter().format(rec))
    assert payload["event"] == "node_start"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "itinerai_agent.x"
    assert payload["node"] == "validate_input"
    assert payload["run_id"] == "-"
    assert payload["timestamp"].endswith("Z")


def test_json_formatter_truncates_long_values():
    rec = _record()
    rec.big = "x" * 600
    payload = json.loads(LC.JsonFormatter().format(rec))
    assert payload["big"].endswith("…")
    assert len(payload["big"]) == 501


def test_json_formatter_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        rec = _record(level=logging.ERROR, msg="node_error", exc_info=sys.exc_info())
    payload = json.loads(LC.JsonFormatter().format(rec))
    assert payload["error"] == "ValueError"
    assert "Traceback" in payload["traceback"]


def test_json_formatter_redacts_secret(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "supersecret-key-1234")
    formatter = LC.JsonFormatter()
    rec = _record()
    rec.detail = "token supersecret-key-1234 aqui"
    rendered = formatter.format(rec)
    assert "supersecret-key-1234" not in rendered
    assert "***REDACTED***" in rendered


def test_json_formatter_no_secret_when_short(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "short")
    assert LC.JsonFormatter()._secret is None


def test_run_id_filter_sets_from_contextvar():
    flt = LC._RunIdFilter()
    rec = _record()
    token = LC.run_id_var.set("run-123")
    try:
        assert flt.filter(rec) is True
        assert rec.run_id == "run-123"
    finally:
        LC.run_id_var.reset(token)


def test_run_id_filter_preserves_existing():
    flt = LC._RunIdFilter()
    rec = _record()
    rec.run_id = "preset"
    flt.filter(rec)
    assert rec.run_id == "preset"


def test_configure_logging_idempotent(monkeypatch, tmp_path, restore_package_logger):
    monkeypatch.setattr(LC, "_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(LC, "_LOG_FILE", tmp_path / "logs" / "itinerai.log")

    logger_1 = LC.configure_logging()
    handler_count = len(logger_1.handlers)
    logger_2 = LC.configure_logging()

    assert logger_1 is logger_2
    assert len(logger_2.handlers) == handler_count
    assert any(getattr(h, LC._HANDLER_SENTINEL, False) for h in logger_2.handlers)
    assert logger_2.propagate is False
    assert (tmp_path / "logs").is_dir()


def test_configure_logging_stderr_mirror(monkeypatch, tmp_path, restore_package_logger):
    monkeypatch.setattr(LC, "_LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(LC, "_LOG_FILE", tmp_path / "logs" / "itinerai.log")
    monkeypatch.setattr(LC, "LOG_TO_STDERR", True)

    logger = LC.configure_logging()
    sentinel = [h for h in logger.handlers if getattr(h, LC._HANDLER_SENTINEL, False)]
    assert len(sentinel) == 2
    names = {type(h).__name__ for h in sentinel}
    assert "RotatingFileHandler" in names
    assert "StreamHandler" in names
