from __future__ import annotations

import sqlite3

import pytest

from traccia.storage import Storage, _validate_sql_identifier


def test_storage_rejects_unsafe_schema_identifiers() -> None:
    with pytest.raises(ValueError, match="Unsafe SQLite identifier"):
        _validate_sql_identifier("sources; drop table sources")


def test_storage_allows_known_safe_identifiers() -> None:
    _validate_sql_identifier("source_category")
    _validate_sql_identifier("person_skill_states")


def test_ensure_columns_adds_missing_column(tmp_path) -> None:
    storage = Storage(tmp_path)
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("create table sample (id text primary key)")

        storage._ensure_columns(connection, table="sample", columns={"created_at": "TEXT"})

        columns = {row["name"] for row in connection.execute("pragma table_info(sample)").fetchall()}
        assert "created_at" in columns
    finally:
        connection.close()
