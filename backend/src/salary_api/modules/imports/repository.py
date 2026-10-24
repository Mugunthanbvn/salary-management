from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from salary_api.core.db import in_chunks
from salary_api.domain.enums import ImportStatus
from salary_api.modules.employees.models import Employee
from salary_api.modules.imports.models import ImportJob


def add(session: Session, job: ImportJob) -> None:
    session.add(job)
    session.flush()


def get(session: Session, job_id: int) -> ImportJob | None:
    return session.get(ImportJob, job_id)


def open_dry_runs(session: Session, user_id: int) -> Sequence[ImportJob]:
    """The user's DRY_RUN jobs, oldest first."""
    query = (
        select(ImportJob)
        .where(ImportJob.created_by == user_id, ImportJob.status == ImportStatus.DRY_RUN)
        .order_by(ImportJob.created_at, ImportJob.id)
    )
    return session.scalars(query).all()


def expire_stale(session: Session, now: datetime) -> None:
    """Mark every DRY_RUN job past its expiry EXPIRED, and drop its rows (salary data)."""
    session.execute(
        update(ImportJob)
        .where(ImportJob.status == ImportStatus.DRY_RUN, ImportJob.expires_at <= now)
        .values(status=ImportStatus.EXPIRED, payload=None, preview=None)
    )


def codes_in_use(session: Session, codes: Sequence[str]) -> set[str]:
    """The employee codes among `codes` that an employee already has."""
    found: set[str] = set()
    for chunk in in_chunks(codes):
        query = select(Employee.employee_code).where(Employee.employee_code.in_(chunk))
        found.update(session.scalars(query))
    return found


def emails_in_use(session: Session, emails: Sequence[str]) -> dict[str, str]:
    """For each of `emails` (normalized) an employee has: that employee's code."""
    found: dict[str, str] = {}
    for chunk in in_chunks(emails):
        query = select(Employee.email, Employee.employee_code).where(Employee.email.in_(chunk))
        found.update((email, code) for email, code in session.execute(query))
    return found
