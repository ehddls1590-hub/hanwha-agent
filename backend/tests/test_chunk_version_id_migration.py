from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "db"
    / "migrations"
    / "versions"
    / "c82f6a1d03b7_add_version_id_to_chunks.py"
)


def test_chunk_version_id_migration_preserves_existing_rows() -> None:
    spec = importlib.util.spec_from_file_location("chunk_version_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE document_versions (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE chunks (id INTEGER PRIMARY KEY)"
            )
        )
        connection.execute(
            text("INSERT INTO chunks (id) VALUES (1)")
        )

        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

        columns = {column["name"] for column in inspect(connection).get_columns("chunks")}
        assert columns == {"id", "version_id", "ord", "kind", "locator", "text"}
        assert connection.execute(
            text("SELECT version_id, ord, kind, locator, text FROM chunks WHERE id = 1")
        ).one() == (None, None, None, None, None)
        assert "ix_chunks_version_id" in {
            index["name"] for index in inspect(connection).get_indexes("chunks")
        }
        foreign_keys = inspect(connection).get_foreign_keys("chunks")
        assert any(
            foreign_key["constrained_columns"] == ["version_id"]
            and foreign_key["referred_table"] == "document_versions"
            for foreign_key in foreign_keys
        )

        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        columns = {column["name"] for column in inspect(connection).get_columns("chunks")}
        assert connection.execute(
            text("SELECT id FROM chunks WHERE id = 1")
        ).scalar_one() == 1
        assert columns == {"id"}

    engine.dispose()
