"""Invariants of employees and salary history (docs/18-implementation-plan.md B4 done-criteria).

- The current salary on `employees` always equals the latest salary record (docs/06 6.2).
- Every mutation writes exactly one audit event, in its own transaction (ADR 0011).
- A list page is three queries whatever its size: the caller, the page, the count.
"""

import random
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Any

import pytest
import time_machine
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, func, select
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal
from salary_api.domain.enums import Level, SalaryReason
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees import service as employees
from salary_api.modules.employees.models import Employee
from salary_api.modules.employees.schemas import EmployeeCreate
from salary_api.modules.reference.models import Country
from salary_api.modules.salaries import repository as salary_history
from salary_api.modules.salaries import service as salaries
from salary_api.modules.salaries.models import SalaryRecord
from salary_api.modules.salaries.schemas import SalaryChangeRequest
from tests.factories import (
    employee_request,
    make_country,
    make_department,
    make_employee,
    make_job_role,
    make_user,
)

EMPLOYEES = "/api/v1/employees"
TODAY = date(2026, 10, 1)  # the frozen_time fixture's date
COUNTRIES = ["DE", "FR", "US", "JP", "IN"]


def _hr(session: Session) -> Principal:
    user = make_user(session, role="HR_MANAGER")
    return Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=user.role)


def _assert_every_current_salary_is_the_latest_record(session: Session) -> None:
    for employee in session.scalars(select(Employee)):
        latest = salary_history.latest_record(session, employee.id)
        assert latest is not None
        country = session.get(Country, employee.country_code)
        assert country is not None
        assert employee.current_salary_record_id == latest.id
        assert (employee.current_base_minor, employee.current_total_minor) == (
            latest.base_minor,
            latest.total_minor,
        )
        assert employee.currency == latest.currency == country.default_currency
        assert (employee.job_role_id, employee.level) == (latest.job_role_id, latest.level)


def _random_change(rng: random.Random, employee: Employee, latest: SalaryRecord) -> dict[str, Any]:
    """A valid salary change: on or after the latest record, never after today."""
    days = rng.randint(0, 120)
    effective_date = min(latest.effective_date + timedelta(days=days), TODAY)
    change: dict[str, Any] = {
        "version": employee.version,
        "effective_date": effective_date,
        "reason": rng.choice([SalaryReason.MERIT, SalaryReason.CORRECTION]),
        "base_minor": rng.randint(3_000_000, 30_000_000),
        "components": [
            {
                "type": "BONUS_TARGET",
                "name": "Target bonus",
                "amount_minor": rng.randint(0, 900_000),
            }
        ][: rng.randint(0, 1)],
    }
    levels = list(Level)
    if rng.random() < 0.3 and employee.level != Level.L6:
        change |= {
            "reason": SalaryReason.PROMOTION,
            "level": levels[levels.index(employee.level) + 1],
        }
    if rng.random() < 0.2:
        change |= {
            "reason": SalaryReason.MARKET_ADJUSTMENT,
            "country_code": rng.choice(COUNTRIES),
        }
    return change


@pytest.mark.parametrize("seed", [7, 42])
def test_the_current_salary_always_equals_the_latest_record(
    db_session: Session, frozen_time: time_machine.Traveller, seed: int
) -> None:
    rng = random.Random(seed)  # noqa: S311  (seeded test data, not security)
    hr = _hr(db_session)
    role = make_job_role(db_session)
    for code in COUNTRIES:
        make_country(db_session, code)
    ids = [
        employees.create_employee(
            db_session,
            hr,
            EmployeeCreate.model_validate(
                employee_request(
                    role.id,
                    email=f"person-{n}@acme.example",
                    country_code=rng.choice(COUNTRIES),
                    hire_date="2020-01-15",
                    level="L1",
                )
            ),
        ).id
        for n in range(4)
    ]
    _assert_every_current_salary_is_the_latest_record(db_session)

    for _ in range(30):
        employee = db_session.get(Employee, rng.choice(ids))
        assert employee is not None
        latest = salary_history.latest_record(db_session, employee.id)
        assert latest is not None
        change = SalaryChangeRequest.model_validate(_random_change(rng, employee, latest))
        salaries.record_salary_change(db_session, hr, employee.id, change)

        _assert_every_current_salary_is_the_latest_record(db_session)


def _create(http: TestClient, session: Session) -> Any:
    make_country(session, "DE")
    return http.post(EMPLOYEES, json=employee_request(make_job_role(session).id))


def _update(http: TestClient, session: Session) -> Any:
    employee = make_employee(session)
    return http.patch(f"{EMPLOYEES}/{employee.id}", json={"version": 1, "first_name": "New"})


def _terminate(http: TestClient, session: Session) -> Any:
    employee = make_employee(session)
    return http.post(f"{EMPLOYEES}/{employee.id}/terminate", json={"version": 1})


def _reactivate(http: TestClient, session: Session) -> Any:
    employee = make_employee(session, status="TERMINATED")
    return http.post(f"{EMPLOYEES}/{employee.id}/reactivate", json={"version": 1})


def _change_salary(http: TestClient, session: Session) -> Any:
    employee = make_employee(session)
    body = {"version": 1, "effective_date": "2026-10-01", "reason": "MERIT", "base_minor": 1}
    return http.post(f"{EMPLOYEES}/{employee.id}/salary-changes", json=body)


MUTATIONS = [
    ("employee.create", _create),
    ("employee.update", _update),
    ("employee.terminate", _terminate),
    ("employee.reactivate", _reactivate),
    ("salary.change", _change_salary),
]


@pytest.mark.parametrize(
    ("action", "mutate"), [pytest.param(action, mutate, id=action) for action, mutate in MUTATIONS]
)
def test_every_mutation_writes_exactly_one_audit_event(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    frozen_time: time_machine.Traveller,
    action: str,
    mutate: Callable[[TestClient, Session], Any],
) -> None:
    response = mutate(as_role("HR_MANAGER"), db_session)

    assert response.status_code in {200, 201}
    assert db_session.scalars(select(AuditEvent.action)).all() == [action]


def test_a_refused_mutation_writes_no_audit_event(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    employee = make_employee(db_session)

    response = as_role("HR_MANAGER").patch(
        f"{EMPLOYEES}/{employee.id}", json={"version": 9, "first_name": "Stale"}
    )

    assert response.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_a_salary_change_whose_audit_write_fails_leaves_nothing_behind(
    db_session: Session, frozen_time: time_machine.Traveller, monkeypatch: pytest.MonkeyPatch
) -> None:
    hr = _hr(db_session)
    employee = make_employee(db_session, base_minor=6_000_000)
    db_session.commit()

    def failing_audit(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("the audit write failed")

    monkeypatch.setattr(salaries, "record_event", failing_audit)
    change = SalaryChangeRequest(
        version=1, effective_date=TODAY, reason=SalaryReason.MERIT, base_minor=7_000_000
    )

    with pytest.raises(RuntimeError):
        salaries.record_salary_change(db_session, hr, employee.id, change)
    db_session.rollback()

    db_session.expire_all()
    assert employee.current_base_minor == 6_000_000
    assert employee.version == 1
    assert len(salary_history.history(db_session, employee.id)) == 1


@contextmanager
def _counting_selects(engine: Engine) -> Iterator[list[str]]:
    statements: list[str] = []

    def count(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", count)


def test_a_list_page_takes_three_queries_however_many_roles_and_departments(
    as_role: Callable[[str], TestClient], db_session: Session, engine: Engine
) -> None:
    for n in range(12):
        department = make_department(db_session, f"Department {n % 4}")
        role = make_job_role(db_session, f"Role {n}", department=department)
        make_employee(db_session, job_role=role)
    http = as_role("VIEWER")
    db_session.expunge_all()  # nothing cached: every row must come from the page query

    with _counting_selects(engine) as selects:
        response = http.get(EMPLOYEES)

    assert response.json()["total"] == 12
    assert len(selects) == 3  # the caller, the page, the count
