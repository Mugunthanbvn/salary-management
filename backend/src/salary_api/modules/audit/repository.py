from sqlalchemy.orm import Session

from salary_api.modules.audit.models import AuditEvent


def add(session: Session, event: AuditEvent) -> None:
    session.add(event)
