from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.modules.audit.models import AuditEvent


def add(session: Session, event: AuditEvent) -> None:
    session.add(event)


def list_since(session: Session, *, action: str, since: datetime) -> Sequence[AuditEvent]:
    """Events of one action strictly after `since`, oldest first."""
    query = (
        select(AuditEvent)
        .where(AuditEvent.action == action, AuditEvent.at > since)
        .order_by(AuditEvent.at, AuditEvent.id)
    )
    return session.scalars(query).all()
