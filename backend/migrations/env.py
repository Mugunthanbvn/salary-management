"""Alembic environment. The database comes from Settings (DATABASE_URL + DATABASE_AUTH_TOKEN).

Tests and scripts may pass an open connection in `config.attributes["connection"]`.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from salary_api.core.config import load_settings
from salary_api.core.db import create_db_engine
from salary_api.core.models import Base

config = context.config
target_metadata = Base.metadata

if config.config_file_name is not None and "connection" not in config.attributes:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(
        url=load_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection: Connection | None = config.attributes.get("connection")
    if connection is not None:
        _run_migrations(connection)
        return

    engine = create_db_engine(load_settings())
    with engine.connect() as new_connection:
        _run_migrations(new_connection)
    engine.dispose()


def _run_migrations(connection: Connection) -> None:
    # Batch mode rebuilds tables for ALTERs that SQLite cannot do in place.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
