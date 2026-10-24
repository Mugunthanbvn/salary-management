"""Salary history queries. There is no update or delete: the history is append-only."""

from sqlalchemy.orm import Session

from salary_api.modules.salaries.models import SalaryRecord


def add_record(session: Session, record: SalaryRecord) -> None:
    session.add(record)
    session.flush()
