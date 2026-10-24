"""Alembic migrations build the schema the models describe (docs/06-data-model.md section 9)."""

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
