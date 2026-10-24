"""Engine and session factory, chosen only by DATABASE_URL (+ DATABASE_AUTH_TOKEN)."""

from typing import Any

from sqlalchemy import URL, Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, Pool, StaticPool

from salary_api.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    url = make_url(settings.database_url)
    connect_args: dict[str, Any] = {}
    if _is_in_memory_sqlite(url):
        connect_args["check_same_thread"] = False
    if settings.database_auth_token and settings.database_auth_token.get_secret_value():
        # Turso: the token goes to the driver, never into the URL or the logs.
        connect_args["auth_token"] = settings.database_auth_token.get_secret_value()
    engine = create_engine(url, poolclass=_pool_class(settings, url), connect_args=connect_args)
    if url.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_foreign_keys)
    if _is_local_sqlite_file(url):
        event.listen(engine, "connect", _tune_local_file)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


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


def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    """SQLite ignores foreign keys unless each connection turns them on."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _tune_local_file(dbapi_connection: Any, _connection_record: Any) -> None:
    """WAL lets readers work during a write; the busy timeout absorbs short write locks."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
