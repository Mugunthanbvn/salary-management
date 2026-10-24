"""Engine and session factory, chosen only by DATABASE_URL (+ DATABASE_AUTH_TOKEN)."""

import sqlite3
from collections.abc import Callable, Generator, Iterator, Sequence
from contextlib import contextmanager
from typing import Any, Final

from sqlalchemy import URL, Connection, Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, Pool, StaticPool

from salary_api.core.config import Settings

BULK_CHUNK_SIZE: Final = 1_000
"""Rows per bulk INSERT or UPDATE and values per IN (...) list: few round trips to the
database, and far below every database's limit on bound parameters."""


def in_chunks[T](values: Sequence[T], size: int = BULK_CHUNK_SIZE) -> Iterator[Sequence[T]]:
    """`values` in consecutive slices of at most `size`."""
    for start in range(0, len(values), size):
        yield values[start : start + size]


def create_db_engine(settings: Settings) -> Engine:
    url = make_url(settings.database_url)
    connect_args: dict[str, Any] = {}
    if _is_in_memory_sqlite(url):
        connect_args["check_same_thread"] = False
    if settings.database_auth_token and settings.database_auth_token.get_secret_value():
        # Turso: the token goes to the driver, never into the URL or the logs.
        connect_args["auth_token"] = settings.database_auth_token.get_secret_value()
    engine = create_engine(
        url,
        poolclass=_pool_class(settings, url),
        connect_args=connect_args,
        hide_parameters=True,  # bound values (salaries, emails) never reach errors or logs
    )
    if url.get_backend_name() == "sqlite":
        stdlib_driver = url.get_driver_name() == "pysqlite"
        on_connect = _sqlite_on_connect(
            local_file=_is_local_sqlite_file(url), stdlib_driver=stdlib_driver
        )
        event.listen(engine, "connect", on_connect)
        if stdlib_driver:
            event.listen(engine, "begin", _begin_immediate)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def foreign_keys_off_for_migrations(connection: Connection) -> Generator[None]:
    """Turn SQLite foreign keys off while migrations run, and back on afterwards.

    Batch migrations rebuild a table by copy, drop and rename; with foreign keys on,
    dropping a table that others reference fails or cascades. Use it before the
    migration transaction starts.
    """
    if connection.dialect.name != "sqlite":
        yield
        return
    _set_sqlite_foreign_keys(connection, enabled=False)
    try:
        yield
    finally:
        _set_sqlite_foreign_keys(connection, enabled=True)


def _set_sqlite_foreign_keys(connection: Connection, *, enabled: bool) -> None:
    statement = "PRAGMA foreign_keys=ON" if enabled else "PRAGMA foreign_keys=OFF"
    if connection.in_transaction():
        connection.commit()  # migrations are done (or not started): close what they left open
    dbapi_connection = connection.connection.dbapi_connection
    if isinstance(dbapi_connection, sqlite3.Connection):
        # Straight to the driver, which opens no transaction of its own: through SQLAlchemy
        # the PRAGMA would run inside BEGIN IMMEDIATE, where SQLite ignores it.
        dbapi_connection.execute(statement)
    else:
        connection.exec_driver_sql(statement)
        connection.commit()


def _pool_class(settings: Settings, url: URL) -> type[Pool] | None:
    if settings.app_env == "production":
        return NullPool  # serverless: a pool does not survive between invocations
    if _is_in_memory_sqlite(url):
        return StaticPool  # one shared connection, so every session sees the same database
    return None  # the dialect's default pool


def _is_in_memory_sqlite(url: URL) -> bool:
    return url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:")


def _is_local_sqlite_file(url: URL) -> bool:
    """A SQLite file on this machine (not in memory, not a hosted libSQL database)."""
    return url.get_backend_name() == "sqlite" and not url.host and not _is_in_memory_sqlite(url)


def _sqlite_on_connect(*, local_file: bool, stdlib_driver: bool) -> Callable[[Any, Any], None]:
    def on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
        # PRAGMAs first: foreign_keys and journal_mode are ignored inside a transaction.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")  # SQLite ignores foreign keys otherwise
        if local_file:
            cursor.execute("PRAGMA journal_mode=WAL")  # readers keep working during a write
            cursor.execute("PRAGMA busy_timeout=5000")  # wait out short write locks
        cursor.close()
        if stdlib_driver:
            # The driver never begins a transaction itself; _begin_immediate does, so
            # SAVEPOINTs and DDL always run inside the enclosing transaction.
            dbapi_connection.isolation_level = None

    return on_connect


def _begin_immediate(connection: Connection) -> None:
    """Start every transaction with BEGIN IMMEDIATE: it takes the write lock at once.

    A deferred BEGIN takes it only at the first write. In WAL mode a transaction that read
    first then fails with "database is locked" if another write committed in between, and
    the busy timeout cannot help. With IMMEDIATE, a second writer waits (busy_timeout)
    for the first to finish. Transactions on one database file therefore run one at a time.
    """
    connection.exec_driver_sql("BEGIN IMMEDIATE")
