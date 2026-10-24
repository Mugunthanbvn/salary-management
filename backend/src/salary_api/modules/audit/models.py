from datetime import datetime
from typing import Any, NoReturn

from sqlalchemy import JSON, Connection, Delete, ForeignKey, Index, String, Update, event
from sqlalchemy.orm import Mapped, Mapper, ORMExecuteState, Session, mapped_column

from salary_api.core.models import Base, UtcDateTime


class AuditEvent(Base):
    """One audited action (docs/06-data-model.md section 4.9). Rows are never changed."""

    __tablename__ = "audit_events"
    __table_args__ = (
        # Per-user Ask rate limit and user activity.
        Index("ix_audit_events_actor_action_at", "actor_id", "action", "at"),
        # The history of one record.
        Index("ix_audit_events_entity", "entity", "entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Null for system actions (seed, migrations) and failed logins.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40))
    # A string, so it fits integer ids, currency codes and country codes.
    entity_id: Mapped[str | None] = mapped_column(String(40))
    # Never holds password hashes, tokens or raw emails of failed logins.
    diff: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    request_id: Mapped[str | None] = mapped_column(String(128))  # the middleware accepts 128
    at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)


class AppendOnlyError(Exception):
    """Audit events are never changed or deleted through the application."""


@event.listens_for(AuditEvent, "before_update")
def refuse_update(
    _mapper: Mapper[AuditEvent], _connection: Connection, _target: AuditEvent
) -> NoReturn:
    raise AppendOnlyError("Audit events cannot be changed.")


@event.listens_for(AuditEvent, "before_delete")
def refuse_delete(
    _mapper: Mapper[AuditEvent], _connection: Connection, _target: AuditEvent
) -> NoReturn:
    raise AppendOnlyError("Audit events cannot be deleted.")


@event.listens_for(Session, "do_orm_execute")
def refuse_bulk_changes(execute_state: ORMExecuteState) -> None:
    """Also refuse `session.execute(update(AuditEvent))` and `delete(...)`, ORM or table form."""
    statement = execute_state.statement
    if isinstance(statement, Update | Delete) and statement.table.compare(AuditEvent.__table__):
        raise AppendOnlyError("Audit events cannot be changed or deleted.")
