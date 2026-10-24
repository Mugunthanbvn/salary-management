"""Write audit events. Callers own the transaction: nothing here commits."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any

import structlog
from sqlalchemy.orm import Session

from salary_api.core.models import utc_now
from salary_api.modules.audit import repository
from salary_api.modules.audit.models import AuditEvent


class AuditAction(StrEnum):
    """The v1 audit actions (docs/glossary.md section 4). Rate limiters count these strings."""

    AUTH_LOGIN = "auth.login"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_LOGOUT = "auth.logout"
    EMPLOYEE_CREATE = "employee.create"
    EMPLOYEE_UPDATE = "employee.update"
    EMPLOYEE_TERMINATE = "employee.terminate"
    EMPLOYEE_REACTIVATE = "employee.reactivate"
    SALARY_CHANGE = "salary.change"
    IMPORT_DRY_RUN = "import.dry_run"
    IMPORT_COMMIT = "import.commit"
    IMPORT_FAIL = "import.fail"
    EXPORT_DOWNLOAD = "export.download"
    INSIGHTS_INDIVIDUALS_VIEW = "insights.individuals_view"
    ASK_QUERY = "ask.query"


# Keyword-only, one argument per column: easy to read at every call site.
def record_event(  # noqa: PLR0913
    session: Session,
    *,
    actor_id: int | None,
    action: AuditAction,
    entity: str,
    entity_id: int | str | None,
    diff: Mapping[str, Any] | None = None,
) -> AuditEvent:
    """Add an audit event to the caller's transaction, so it commits or rolls back with it.

    `actor_id` is None for system actions and failed logins. The request id comes from the
    logging context that the request id middleware binds.
    """
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=None if entity_id is None else str(entity_id),
        diff=None if diff is None else dict(diff),
        request_id=structlog.contextvars.get_contextvars().get("request_id"),
        at=utc_now(),
    )
    repository.add(session, event)
    return event


def events_since(session: Session, *, action: AuditAction, since: datetime) -> Sequence[AuditEvent]:
    """Events of one action strictly after `since`, oldest first (rate limits count these)."""
    return repository.list_since(session, action=action, since=since)
