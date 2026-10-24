"""Engine and session factory. The database is chosen only by DATABASE_URL."""

from typing import Any

from sqlalchemy import URL, Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from salary_api.core.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    url = make_url(settings.database_url)
    if _is_in_memory_sqlite(url):
        # One shared connection, so every session sees the same in-memory database.
        engine = create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(url)
    if url.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _is_in_memory_sqlite(url: URL) -> bool:
    return url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:")


def _enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
    """SQLite ignores foreign keys unless each connection turns them on."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
