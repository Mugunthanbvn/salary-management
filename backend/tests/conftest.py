"""Shared fixtures: settings, in-memory database, rolled-back session, test client, frozen time.

Sockets are disabled for every test (pytest-socket, see addopts in pyproject.toml).
"""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
import time_machine
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import settings as hypothesis_settings
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.db import create_db_engine
from salary_api.core.deps import get_session
from salary_api.main import create_app
from tests.factories import make_settings

# HYPOTHESIS_PROFILE=ci (set in CI) makes property tests derandomized and repeatable.
hypothesis_settings.register_profile("ci", derandomize=True, max_examples=100, deadline=None)
hypothesis_settings.register_profile("dev", max_examples=200, deadline=None)
hypothesis_settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

FROZEN_NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


@contextmanager
def rolled_back_session(engine: Engine) -> Iterator[Session]:
    """A session whose work, including commits, is rolled back at the end.

    The outer transaction is never committed. The session joins it with a SAVEPOINT,
    so code under test may call commit() and the test still leaves nothing behind.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture(scope="session")
def settings() -> Settings:
    return make_settings()


@pytest.fixture(scope="session")
def engine(settings: Settings) -> Iterator[Engine]:
    """One in-memory database per test worker (StaticPool shares its single connection)."""
    engine = create_db_engine(settings)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    with rolled_back_session(engine) as session:
        yield session


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI, db_session: Session) -> Iterator[TestClient]:
    def session_override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def frozen_time() -> Iterator[time_machine.Coordinates]:
    with time_machine.travel(FROZEN_NOW, tick=False) as traveller:
        yield traveller
