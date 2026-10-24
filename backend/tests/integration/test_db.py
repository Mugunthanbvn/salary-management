"""Engine behaviour (docs/06-data-model.md section 7). Each test builds its own engine."""

from pathlib import Path

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

from salary_api.core.config import Settings
from salary_api.core.db import create_db_engine
from tests.factories import make_settings


@pytest.mark.sqlite_only
@pytest.mark.parametrize("database", ["memory", "file"])
def test_sqlite_connections_reject_an_orphan_foreign_key(tmp_path: Path, database: str) -> None:
    url = "sqlite://" if database == "memory" else f"sqlite:///{tmp_path / 'app.db'}"
    engine = create_db_engine(make_settings(database_url=url))
    metadata = MetaData()
    Table("parents", metadata, Column("id", Integer, primary_key=True))
    children = Table(
        "children",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey("parents.id"), nullable=False),
    )
    metadata.create_all(engine)

    with engine.connect() as connection, pytest.raises(IntegrityError, match="FOREIGN KEY"):
        connection.execute(insert(children).values(id=1, parent_id=999))

    engine.dispose()


@pytest.mark.sqlite_only
def test_file_databases_use_wal_journal_and_a_busy_timeout(tmp_path: Path) -> None:
    engine = create_db_engine(make_settings(database_url=f"sqlite:///{tmp_path / 'app.db'}"))

    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar()
        busy_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar()

    assert (journal_mode, busy_timeout) == ("wal", 5000)
    engine.dispose()


def test_production_engine_does_not_pool_connections() -> None:
    # model_construct skips the production checks, which have their own tests.
    settings = Settings.model_construct(app_env="production", database_url="sqlite://")

    engine = create_db_engine(settings)

    assert isinstance(engine.pool, NullPool)

