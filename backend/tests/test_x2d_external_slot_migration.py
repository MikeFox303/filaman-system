from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "normalize_x2d_external_slots.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("normalize_x2d_external_slots", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _schema(conn) -> None:
    conn.exec_driver_sql(
        "CREATE TABLE printers (id INTEGER PRIMARY KEY, driver_key VARCHAR(100) NOT NULL)"
    )
    conn.exec_driver_sql(
        "CREATE TABLE printer_slots ("
        "id INTEGER PRIMARY KEY, printer_id INTEGER NOT NULL, slot_no INTEGER NOT NULL, "
        "name VARCHAR(100), custom_fields JSON, UNIQUE(printer_id, slot_no))"
    )
    conn.exec_driver_sql(
        "CREATE TABLE printer_slot_assignments ("
        "slot_id INTEGER PRIMARY KEY, spool_id INTEGER, present BOOLEAN NOT NULL DEFAULT 0, "
        "rfid_uid VARCHAR(100), external_id VARCHAR(100), inserted_at DATETIME, "
        "updated_at DATETIME, meta JSON)"
    )
    conn.exec_driver_sql(
        "CREATE TABLE printer_slot_events (id INTEGER PRIMARY KEY, slot_id INTEGER NOT NULL)"
    )


def _rows(conn, sql: str):
    return conn.execute(sa.text(sql)).mappings().all()


def test_renames_legacy_slot_in_place_when_canonical_slot_is_missing():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        _schema(conn)
        conn.exec_driver_sql("INSERT INTO printers VALUES (1, 'bambuddy')")
        conn.exec_driver_sql(
            "INSERT INTO printer_slots VALUES (10, 1, 1255, 'External Tray', '{\"slot_index\":\"255-255\"}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slot_assignments "
            "(slot_id, spool_id, present, updated_at, meta) "
            "VALUES (10, 42, 1, CURRENT_TIMESTAMP, '{\"source\":\"legacy\"}')"
        )
        conn.exec_driver_sql("INSERT INTO printer_slot_events VALUES (1, 10)")

        migration._migrate_connection(conn)

        slots = _rows(conn, "SELECT * FROM printer_slots")
        assert len(slots) == 1
        assert slots[0]["id"] == 10
        assert slots[0]["slot_no"] == 1001
        assert "255-1" in slots[0]["custom_fields"]
        assignment = _rows(conn, "SELECT * FROM printer_slot_assignments")[0]
        assert assignment["slot_id"] == 10
        assert assignment["spool_id"] == 42
        event = _rows(conn, "SELECT * FROM printer_slot_events")[0]
        assert event["slot_id"] == 10


def test_merges_legacy_assignment_into_empty_canonical_slot_and_reparents_history():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        _schema(conn)
        conn.exec_driver_sql("INSERT INTO printers VALUES (1, 'bambuddy')")
        conn.exec_driver_sql(
            "INSERT INTO printer_slots VALUES (10, 1, 1255, 'External Tray', '{\"slot_index\":\"255-255\"}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slots VALUES (20, 1, 1001, 'External Tray', '{\"slot_index\":\"255-1\"}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slot_assignments "
            "(slot_id, spool_id, present, rfid_uid, external_id, updated_at, meta) "
            "VALUES (10, 42, 1, 'rfid-old', 'bb-42', CURRENT_TIMESTAMP, '{\"old\":1}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slot_assignments "
            "(slot_id, spool_id, present, updated_at, meta) "
            "VALUES (20, NULL, 0, CURRENT_TIMESTAMP, '{\"new\":2}')"
        )
        conn.exec_driver_sql("INSERT INTO printer_slot_events VALUES (1, 10)")

        migration._migrate_connection(conn)

        slots = _rows(conn, "SELECT * FROM printer_slots ORDER BY id")
        assert [row["id"] for row in slots] == [20]
        assert slots[0]["slot_no"] == 1001
        assignment = _rows(conn, "SELECT * FROM printer_slot_assignments")[0]
        assert assignment["slot_id"] == 20
        assert assignment["spool_id"] == 42
        assert assignment["present"] == 1
        assert assignment["rfid_uid"] == "rfid-old"
        assert assignment["external_id"] == "bb-42"
        assert '"old": 1' in assignment["meta"] or '"old":1' in assignment["meta"]
        assert '"new": 2' in assignment["meta"] or '"new":2' in assignment["meta"]
        event = _rows(conn, "SELECT * FROM printer_slot_events")[0]
        assert event["slot_id"] == 20


def test_keeps_current_canonical_spool_on_conflict_and_is_idempotent():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        _schema(conn)
        conn.exec_driver_sql("INSERT INTO printers VALUES (1, 'bambuddy')")
        conn.exec_driver_sql(
            "INSERT INTO printer_slots VALUES (10, 1, 1254, 'External Tray', '{\"slot_index\":\"255-254\"}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slots VALUES (20, 1, 1000, 'External Tray', '{\"slot_index\":\"255-0\"}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slot_assignments "
            "(slot_id, spool_id, present, updated_at, meta) "
            "VALUES (10, 42, 1, CURRENT_TIMESTAMP, '{\"legacy\":1}')"
        )
        conn.exec_driver_sql(
            "INSERT INTO printer_slot_assignments "
            "(slot_id, spool_id, present, updated_at, meta) "
            "VALUES (20, 99, 1, CURRENT_TIMESTAMP, '{\"canonical\":1}')"
        )

        migration._migrate_connection(conn)
        migration._migrate_connection(conn)

        slots = _rows(conn, "SELECT * FROM printer_slots")
        assert len(slots) == 1
        assert slots[0]["slot_no"] == 1000
        assignment = _rows(conn, "SELECT * FROM printer_slot_assignments")[0]
        assert assignment["spool_id"] == 99


def test_ignores_non_bambuddy_printers():
    migration = _load_migration()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        _schema(conn)
        conn.exec_driver_sql("INSERT INTO printers VALUES (1, 'other')")
        conn.exec_driver_sql(
            "INSERT INTO printer_slots VALUES (10, 1, 1255, 'External Tray', '{\"slot_index\":\"255-255\"}')"
        )

        migration._migrate_connection(conn)

        slot = _rows(conn, "SELECT * FROM printer_slots")[0]
        assert slot["slot_no"] == 1255
