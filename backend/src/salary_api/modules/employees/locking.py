"""Optimistic locking of employees (ADR 0013), shared by the employee and salary services.

Every change names the version the client read. The service refuses a stale one, and the
mapper's `WHERE version = <read version>` catches a change committed in between.
"""

from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from salary_api.core.errors import NotFound, VersionConflict
from salary_api.modules.employees import repository
from salary_api.modules.employees.models import Employee


def get(session: Session, employee_id: int) -> Employee:
    """The employee with role, department and current salary loaded (NotFound otherwise)."""
    employee = repository.get_detail(session, employee_id)
    if employee is None:
        raise NotFound(f"Employee {employee_id} was not found.")
    return employee


def get_version(session: Session, employee_id: int, version: int) -> Employee:
    """The employee, if `version` is still the current one (VersionConflict otherwise)."""
    employee = get(session, employee_id)
    if employee.version != version:
        raise _version_conflict(employee_id, employee.version)
    return employee


def commit_versioned(session: Session, employee_id: int) -> None:
    """Commit. A change committed by someone else since the read matches no row in the
    versioned UPDATE, so it rolls back and becomes a VersionConflict."""
    try:
        session.commit()
    except StaleDataError:
        session.rollback()
        raise _version_conflict(
            employee_id, repository.current_version(session, employee_id) or 0
        ) from None


def _version_conflict(employee_id: int, current_version: int) -> VersionConflict:
    return VersionConflict(
        f"Employee {employee_id} was changed by someone else. Reload and try again.",
        current_version=current_version,
    )
