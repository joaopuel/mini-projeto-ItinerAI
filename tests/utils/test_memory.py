"""Testes de `itinerai_agent/utils/memory.py` (SQLite, registro único)."""

import sqlite3
from datetime import datetime

import pytest

from itinerai_agent.utils import memory as M
from itinerai_agent.utils.memory import TripMemory


@pytest.fixture
def db(tmp_path):
    return tmp_path / "m.db"


def _raw(db_path, query, params=()):
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(query, params).fetchall()
    finally:
        connection.close()


def test_init_db_creates_table(db):
    M.init_db(db_path=db)
    names = [
        row[0]
        for row in _raw(db, "SELECT name FROM sqlite_master WHERE type = 'table'")
    ]
    assert "trip_memory" in names


def test_save_then_load_roundtrip(db):
    M.save_trip_memory(
        TripMemory(destination="Lisboa", num_days=3, completed=True), db_path=db
    )
    loaded = M.load_trip_memory(db_path=db)
    assert loaded is not None
    assert loaded.destination == "Lisboa"
    assert loaded.num_days == 3
    assert loaded.completed is True
    datetime.fromisoformat(loaded.updated_at)  # não levanta


def test_save_is_single_row_upsert(db):
    M.save_trip_memory(TripMemory(destination="Paris", num_days=2), db_path=db)
    M.save_trip_memory(TripMemory(destination="Roma", num_days=5), db_path=db)
    assert _raw(db, "SELECT COUNT(*) FROM trip_memory")[0][0] == 1
    assert M.load_trip_memory(db_path=db).destination == "Roma"


def test_load_none_when_empty(db):
    assert M.load_trip_memory(db_path=db) is None


@pytest.mark.parametrize("value, expected", [(False, 0), (True, 1)])
def test_completed_persisted_as_int(db, value, expected):
    M.save_trip_memory(
        TripMemory(destination="X", completed=value), db_path=db
    )
    assert _raw(db, "SELECT completed FROM trip_memory WHERE id = 1")[0][0] == expected


def test_updated_at_is_overwritten(db):
    M.save_trip_memory(
        TripMemory(destination="X", updated_at="1999-01-01T00:00:00"), db_path=db
    )
    loaded = M.load_trip_memory(db_path=db)
    assert loaded.updated_at != "1999-01-01T00:00:00"
    assert len(loaded.updated_at) == 19


def test_check_constraint_rejects_non_1_id(db):
    M.init_db(db_path=db)
    with pytest.raises(sqlite3.IntegrityError):
        _raw(
            db,
            "INSERT INTO trip_memory (id, destination, num_days, completed, updated_at) "
            "VALUES (2, 'X', 1, 0, 't')",
        )


def test_default_path_used_when_db_path_none(monkeypatch, tmp_path):
    default_db = tmp_path / "def.db"
    monkeypatch.setattr(M, "MEMORY_DB_PATH", default_db)
    M.save_trip_memory(TripMemory(destination="D"))
    assert M.load_trip_memory().destination == "D"
    assert default_db.exists()
