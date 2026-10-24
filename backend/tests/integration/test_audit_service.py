"""The audit writer joins the caller's transaction (ADR 0011, docs/glossary.md section 4)."""

import pytest
import structlog
import time_machine
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.audit.service import AuditAction, record_event
from tests.conftest import FROZEN_NOW

GLOSSARY_V1_ACTIONS = [
    "auth.login",
    "auth.login_failed",
    "auth.logout",
    "employee.create",
    "employee.update",
    "employee.terminate",
    "employee.reactivate",
    "salary.change",
    "import.dry_run",
    "import.commit",
    "import.fail",
    "export.download",
    "insights.individuals_view",
    "ask.query",
    "ask.answer",
]


def _count_events(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AuditEvent)) or 0


def test_audit_actions_are_the_glossary_v1_actions() -> None:
    assert [action.value for action in AuditAction] == GLOSSARY_V1_ACTIONS


def test_an_event_is_written_with_the_time_and_the_request_id(
    db_session: Session, frozen_time: time_machine.Traveller
) -> None:
    with structlog.contextvars.bound_contextvars(request_id="req-7"):
        record_event(
            db_session,
            actor_id=None,
            action=AuditAction.AUTH_LOGIN_FAILED,
            entity="auth",
            entity_id=42,
            diff={"email_hash": "ab12"},
        )
    db_session.commit()

    event = db_session.scalars(select(AuditEvent)).one()
    assert (event.action, event.entity, event.entity_id, event.diff) == (
        "auth.login_failed",
        "auth",
        "42",
        {"email_hash": "ab12"},
    )
    assert (event.at, event.request_id, event.actor_id) == (FROZEN_NOW, "req-7", None)


def test_an_event_is_rolled_back_with_the_failing_change_it_describes(
    db_session: Session,
) -> None:
    def failing_use_case() -> None:
        record_event(
            db_session,
            actor_id=None,
            action=AuditAction.EMPLOYEE_UPDATE,
            entity="employee",
            entity_id=7,
            diff={"department_id": [1, 2]},
        )
        raise RuntimeError("the change failed after the event was recorded")

    with pytest.raises(RuntimeError):
        failing_use_case()
    db_session.rollback()

    assert _count_events(db_session) == 0
