"""Engine behaviour (docs/06-data-model.md section 7). Each test builds its own engine."""

from pathlib import Path

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, insert
from sqlalchemy.exc import IntegrityError

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
