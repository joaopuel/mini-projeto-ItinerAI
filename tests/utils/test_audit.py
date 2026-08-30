"""Testes de `itinerai_agent/utils/audit.py` — trilha de auditoria (T05/#16),
cobertos aqui pela T07/#18."""

import sqlite3

import pytest

from itinerai_agent.utils import audit as A
from itinerai_agent.utils.audit import AuditStep


@pytest.fixture
def db(tmp_path):
    return tmp_path / "a.db"


def _step(run_id, step, step_type, status, duration_ms=None, error=None):
    return AuditStep(
        run_id=run_id,
        step=step,
        step_type=step_type,
        status=status,
        duration_ms=duration_ms,
        error=error,
    )


def test_init_db_creates_table_and_index(db):
    A.init_db(db_path=db)
    connection = sqlite3.connect(db)
    try:
        objs = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
            )
        }
    finally:
        connection.close()
    assert "execution_audit" in objs
    assert "ix_execution_audit_run_id" in objs


def test_record_and_load_trail_ordered(db):
    A.record_audit_step(_step("r1", "validate_input", "node", "ok", 12.3), db_path=db)
    A.record_audit_step(_step("r1", "call_llm", "node", "ok", 45.6), db_path=db)
    A.record_audit_step(_step("r1", "graph_invoke", "turn", "ok", 99.9), db_path=db)
    trail = A.load_audit_trail("r1", db_path=db)
    assert [s.step for s in trail] == ["validate_input", "call_llm", "graph_invoke"]
    assert trail[0].duration_ms == 12.3
    assert trail[0].created_at.endswith("Z")


def test_record_overwrites_created_at(db):
    A.record_audit_step(
        AuditStep(
            run_id="r1",
            step="s",
            step_type="node",
            status="ok",
            created_at="old",
        ),
        db_path=db,
    )
    stored = A.load_audit_trail("r1", db_path=db)[0].created_at
    assert stored != "old"
    assert stored.endswith("Z")


def test_load_trail_empty_is_list(db):
    assert A.load_audit_trail("nope", db_path=db) == []


def test_load_trail_filters_by_run_id(db):
    A.record_audit_step(_step("r1", "a", "node", "ok"), db_path=db)
    A.record_audit_step(_step("r2", "b", "node", "ok"), db_path=db)
    trail = A.load_audit_trail("r1", db_path=db)
    assert [s.run_id for s in trail] == ["r1"]


def test_format_empty_exact_string(db):
    assert (
        A.format_audit_trail("missing", db_path=db)
        == "Nenhum passo de auditoria encontrado para run_id missing."
    )


def test_format_full_trail(db):
    rows = [
        ("wikipedia_fetch", "tool", "retry", None, "Timeout"),
        ("wikipedia_fetch", "tool", "ok", 800.0, None),
        ("llm_extraction", "tool", "fallback", 50.0, "no_json"),
        ("build_itinerary", "tool", "ok", 5.0, None),
        ("call_llm", "node", "error", 3.0, "ValueError"),
        ("graph_invoke", "turn", "ok", 1234.5, None),
    ]
    for step, step_type, status, ms, err in rows:
        A.record_audit_step(_step("r1", step, step_type, status, ms, err), db_path=db)

    text = A.format_audit_trail("r1", db_path=db)
    assert "Trilha de auditoria — run_id r1" in text
    assert "  (Timeout)" in text
    assert "Passo mais lento: wikipedia_fetch (800.0 ms)" in text
    assert "Total (turno): 1234.5 ms" in text
    assert "6 passos · 1 retries · 1 fallbacks · 1 erros" in text


def test_format_none_duration_renders_dash(db):
    A.record_audit_step(_step("r1", "x", "node", "retry"), db_path=db)
    text = A.format_audit_trail("r1", db_path=db)
    assert "—" in text
    assert "Passo mais lento" not in text
    assert "Total (turno)" not in text
    assert "1 passos · 1 retries · 0 fallbacks · 0 erros" in text


def test_record_audit_step_propagates_io_error(tmp_path):
    # tmp_path é um diretório: sqlite3.connect nele levanta OperationalError.
    with pytest.raises(sqlite3.OperationalError):
        A.record_audit_step(_step("r1", "s", "node", "ok"), db_path=tmp_path)


def test_try_record_writes_row():
    A.try_record("r1", "validate_input", "node", "ok", 1.0)
    trail = A.load_audit_trail("r1")
    assert len(trail) == 1
    assert trail[0].status == "ok"


def test_try_record_blank_run_id_becomes_dash():
    A.try_record("", "s", "node", "ok")
    assert A.load_audit_trail("-")[0].run_id == "-"


def test_try_record_swallows_and_logs(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disco cheio")

    calls = []
    monkeypatch.setattr(A, "record_audit_step", boom)
    monkeypatch.setattr(A.logger, "warning", lambda *a, **k: calls.append((a, k)))

    A.try_record("r1", "s", "node", "ok")  # não levanta

    assert calls[0][0][0] == "audit_write_failed"
    assert calls[0][1]["extra"]["error"] == "OSError"


def test_default_path_branch(monkeypatch, tmp_path):
    default_db = tmp_path / "d.db"
    monkeypatch.setattr(A, "AUDIT_DB_PATH", default_db)
    A.record_audit_step(_step("r", "s", "node", "ok"), db_path=None)
    assert default_db.exists()
