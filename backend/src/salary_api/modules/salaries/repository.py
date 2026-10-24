"""Salary history queries. There is no update or delete: the history is append-only."""

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, joinedload, selectinload

from salary_api.core.db import in_chunks
from salary_api.domain.enums import ComponentType
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord


def add_record(session: Session, record: SalaryRecord) -> None:
    session.add(record)
    session.flush()


def highest_record_id(session: Session) -> int:
    return session.scalar(select(func.max(SalaryRecord.id))) or 0


def insert_records(session: Session, rows: Sequence[Mapping[str, Any]]) -> None:
    """Bulk INSERT of new salary records (ids included), in chunks. Inserts only."""
    for chunk in in_chunks(rows):
        session.execute(insert(SalaryRecord), chunk)


def insert_components(session: Session, rows: Sequence[Mapping[str, Any]]) -> None:
    """Bulk INSERT of the components of records inserted in the same transaction."""
    for chunk in in_chunks(rows):
        session.execute(insert(SalaryComponent), chunk)


def component_totals(
    session: Session, record_ids: Sequence[int]
) -> dict[int, dict[ComponentType, int]]:
    """For each record that has components: the sum of its components of each type."""
    totals: dict[int, dict[ComponentType, int]] = {}
    for chunk in in_chunks(record_ids):
        query = (
            select(
                SalaryComponent.salary_record_id,
                SalaryComponent.type,
                func.sum(SalaryComponent.amount_minor),
            )
            .where(SalaryComponent.salary_record_id.in_(chunk))
            .group_by(SalaryComponent.salary_record_id, SalaryComponent.type)
        )
        for record_id, component_type, total in session.execute(query):
            totals.setdefault(record_id, {})[component_type] = total
    return totals


def latest_record(session: Session, employee_id: int) -> SalaryRecord | None:
    """The current record: the greatest (effective_date, id)."""
    query = (
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc())
        .limit(1)
    )
    return session.scalars(query).first()


def history(session: Session, employee_id: int) -> Sequence[SalaryRecord]:
    """Every record of the employee, oldest first, with role, components and author loaded."""
    query = (
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id)
        .options(
            joinedload(SalaryRecord.job_role),
            joinedload(SalaryRecord.changed_by_user),
            selectinload(SalaryRecord.components),
        )
        .order_by(SalaryRecord.effective_date, SalaryRecord.id)
    )
    return session.scalars(query).all()
