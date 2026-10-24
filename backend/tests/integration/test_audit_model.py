"""The audit_events table (docs/06-data-model.md section 4.9): append-only, actor optional."""

from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import String, Table, delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from salary_api.core.permissions import Role
from salary_api.modules.audit.models import AppendOnlyError, AuditEvent
from salary_api.modules.users.models import User
from tests.conftest import FROZEN_NOW


def _event(actor_id: int | None = None) -> AuditEvent:
    return AuditEvent(
        actor_id=actor_id,
        action="auth.login_failed",
        entity="auth",
        entity_id=None,
        diff={"email_hash": "ab12"},
        request_id="req-1",
        at=FROZEN_NOW,
    )


def test_an_event_without_an_actor_is_stored_with_its_json_diff(db_session: Session) -> None:
    db_session.add(_event(actor_id=None))
    db_session.flush()
    db_session.expunge_all()

    stored = db_session.scalars(select(AuditEvent)).one()

    assert (stored.actor_id, stored.action, stored.entity, stored.entity_id) == (
        None,
        "auth.login_failed",
        "auth",
        None,
    )
    assert (stored.diff, stored.request_id, stored.at) == (
        {"email_hash": "ab12"},
        "req-1",
        FROZEN_NOW,
    )


def test_an_event_actor_must_be_an_existing_user(db_session: Session) -> None:
    db_session.add(_event(actor_id=999))

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        db_session.flush()


def test_an_event_can_reference_an_existing_user_as_actor(db_session: Session) -> None:
    user = User(email="ana@acme.example", full_name="Ana", password_hash="x", role=Role.ADMIN)
    db_session.add(user)
    db_session.flush()

    db_session.add(_event(actor_id=user.id))
    db_session.flush()

    assert db_session.scalars(select(AuditEvent.actor_id)).one() == user.id


def test_events_cannot_be_changed_after_they_are_written(db_session: Session) -> None:
    event = _event()
    db_session.add(event)
    db_session.flush()

    event.action = "auth.login"

    with pytest.raises(AppendOnlyError):
        db_session.flush()


def test_events_cannot_be_deleted(db_session: Session) -> None:
    event = _event()
    db_session.add(event)
    db_session.flush()

    db_session.delete(event)

    with pytest.raises(AppendOnlyError):
        db_session.flush()


AUDIT_TABLE = cast(Table, AuditEvent.__table__)


@pytest.mark.parametrize(
    "statement",
    [
        pytest.param(update(AuditEvent).values(action="tampered"), id="orm update"),
        pytest.param(delete(AuditEvent), id="orm delete"),
        pytest.param(update(AUDIT_TABLE).values(action="tampered"), id="table update"),
        pytest.param(delete(AUDIT_TABLE), id="table delete"),
    ],
)
def test_bulk_statements_cannot_change_or_delete_events(
    db_session: Session, statement: Any
) -> None:
    db_session.add(_event())
    db_session.flush()

    with pytest.raises(AppendOnlyError):
        db_session.execute(statement)


def test_bulk_inserts_of_events_are_allowed(db_session: Session) -> None:
    db_session.execute(
        insert(AuditEvent).values(action="auth.logout", entity="user", at=FROZEN_NOW)
    )

    assert db_session.scalars(select(AuditEvent.action)).all() == ["auth.logout"]


def test_the_request_id_column_fits_the_longest_request_id_the_middleware_accepts(
    client: TestClient,
) -> None:
    longest = "r" * 128
    response = client.get("/api/v1/health", headers={"X-Request-ID": longest})
    column_type = AUDIT_TABLE.c.request_id.type

    assert response.headers["X-Request-ID"] == longest  # accepted as is
    assert isinstance(column_type, String)
    assert column_type.length is not None
    assert column_type.length >= len(longest)
