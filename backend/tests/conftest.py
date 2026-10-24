"""Shared fixtures: settings, in-memory database, rolled-back session, test client, frozen time.

Sockets are disabled for every test (pytest-socket, see addopts in pyproject.toml).
"""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
import time_machine
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import settings as hypothesis_settings
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from salary_api.core.config import Settings
from salary_api.core.db import create_db_engine, create_session_factory
from salary_api.core.deps import get_password_hasher, get_session
from salary_api.core.permissions import Role
from salary_api.core.security import SESSION_COOKIE, create_access_token
from salary_api.main import create_app
from salary_api.modules.users.models import User
from tests.factories import FAST_PASSWORD_HASHER, make_settings, make_user

# HYPOTHESIS_PROFILE=ci (set in CI) makes property tests derandomized and repeatable.
hypothesis_settings.register_profile("ci", derandomize=True, max_examples=100, deadline=None)
hypothesis_settings.register_profile("dev", max_examples=200, deadline=None)
hypothesis_settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

FROZEN_NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def upgrade_to_head(engine: Engine) -> None:
    """Build the schema from the Alembic migrations, so every test run checks them."""
    config = Config(ALEMBIC_INI)
    with engine.connect() as connection:  # not begin(): env.py manages the transaction
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


@contextmanager
def rolled_back_session(engine: Engine) -> Iterator[Session]:
    """A session whose work, including commits, is rolled back at the end.

    The outer transaction is never committed. The session joins it with a SAVEPOINT,
    so code under test may call commit() and the test still leaves nothing behind.
    It comes from the app's own session factory, so it has the same options.
    """
    with engine.connect() as connection:
        transaction = connection.begin()
        session = create_session_factory(engine)(
            bind=connection, join_transaction_mode="create_savepoint"
        )
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
    """One migrated in-memory database per test worker (StaticPool shares its connection)."""
    engine = create_db_engine(settings)
    upgrade_to_head(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    with rolled_back_session(engine) as session:
        yield session


def create_test_app(settings: Settings) -> FastAPI:
    """The real app, hashing passwords with cheap argon2 parameters so tests stay fast."""
    app = create_app(settings)
    app.dependency_overrides[get_password_hasher] = lambda: FAST_PASSWORD_HASHER
    return app


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_test_app(settings)


@pytest.fixture
def client(app: FastAPI, db_session: Session) -> Iterator[TestClient]:
    def session_override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as test_client:
        yield test_client


def signed_in_client(app: FastAPI, user: User, settings: Settings) -> TestClient:
    """A client whose session cookie belongs to `user`, minted without a login call."""
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return TestClient(app, cookies={SESSION_COOKIE: token})


@pytest.fixture
def as_role(
    app: FastAPI, client: TestClient, db_session: Session, settings: Settings
) -> Callable[[Role | str], TestClient]:
    """`as_role("VIEWER").get(...)`: a client signed in as a new user of that role.

    The cookie is minted directly, so no `auth.login` event is written. It uses the
    `client` fixture's app, so requests share the test's rolled-back session.
    """

    def sign_in_as(role: Role | str) -> TestClient:
        return signed_in_client(app, make_user(db_session, role=role), settings)

    return sign_in_as


@pytest.fixture
def frozen_time() -> Iterator[time_machine.Traveller]:
    with time_machine.travel(FROZEN_NOW, tick=False) as traveller:
        yield traveller
