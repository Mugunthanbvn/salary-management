"""Alembic migrations build the schema the models describe (docs/06-data-model.md section 9)."""

import io
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from salary_api.core.db import create_db_engine
from salary_api.core.models import Base
from tests.conftest import ALEMBIC_INI
from tests.factories import make_settings


def test_upgrade_head_on_an_empty_database_matches_the_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)  # env.py reads DATABASE_URL from Settings

    command.upgrade(Config(ALEMBIC_INI), "head")

    engine = create_db_engine(make_settings(database_url=database_url))
    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert differences == []


def test_on_postgres_the_migration_adds_the_current_salary_record_foreign_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Offline (--sql) rendering needs only the dialect, not a server.
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/salary")
    config = Config(ALEMBIC_INI)
    config.output_buffer = io.StringIO()

    command.upgrade(config, "0003:0004", sql=True)

    sql = config.output_buffer.getvalue()
    assert (
        "ALTER TABLE employees ADD CONSTRAINT fk_employees_current_salary_record_id_salary_records "
        "FOREIGN KEY(current_salary_record_id) REFERENCES salary_records (id)"
    ) in sql
