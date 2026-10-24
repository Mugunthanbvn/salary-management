"""Insight endpoints run a fixed number of queries, however many employees match.

The database filters and sorts and returns the needed columns; Python does the maths
(docs/19-performance.md section 4.2). No query per group or per employee (no N+1).
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.domain.enums import Level
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import (
    CohortQuery,
    CompareMetric,
    InsightQuery,
    JobTitleQuery,
    PayEquityQuery,
    PayEquityView,
    TopEarnersQuery,
)
from salary_api.modules.reference.models import JobFamily, JobRole
from tests.factories import (
    make_department,
    make_employee,
    make_fx_rates,
    make_job_role,
    make_pay_band,
    make_user,
)


@contextmanager
def _counting_selects(session: Session) -> Iterator[list[str]]:
    statements: list[str] = []

    def record(*args: Any) -> None:
        statement: str = args[2]
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    connection = session.connection()
    event.listen(connection, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", record)


COHORTS = [(country, level) for country in ("DE", "IN") for level in ("L2", "L3")]


def _roles_and_bands(session: Session) -> list[JobRole]:
    """Three departments with one role each, banded in two countries at two levels."""
    make_fx_rates(session)
    roles: list[JobRole] = []
    for department in ("Customer Success", "Engineering", "Sales"):
        role = make_job_role(
            session,
            f"{department} role",
            department=make_department(session, department),
            family=JobFamily.SALES,
        )
        for country, level in COHORTS:
            make_pay_band(session, job_role=role, level=level, country=country)
        roles.append(role)
    return roles


def _hire_one_per_cohort(session: Session, roles: list[JobRole]) -> None:
    for number, role in enumerate(roles):
        for country, level in COHORTS:
            make_employee(
                session,
                job_role=role,
                level=level,
                country=country,
                base_minor=6_000_000 + number * 1_000,
            )


CALLS: dict[str, tuple[int, Callable[[Session, Principal, int], object]]] = {
    # name: (the most SELECTs allowed, the call)
    "overview": (2, lambda s, hr, _r: service.overview(s, hr, InsightQuery())),
    "by_department": (2, lambda s, hr, _r: service.by_department(s, hr, InsightQuery())),
    "by_job_title": (
        2,
        lambda s, hr, _r: service.by_job_title(
            s, hr, JobTitleQuery(country="DE", split_by_level=True)
        ),
    ),
    "department_cost": (2, lambda s, hr, _r: service.department_cost(s, hr, InsightQuery())),
    "top_earners": (2, lambda s, hr, _r: service.top_earners(s, hr, TopEarnersQuery(country="DE"))),
    "pay_equity_cohorts": (3, lambda s, hr, _r: service.pay_equity(s, hr, PayEquityQuery())),
    "pay_equity_departments": (
        3,
        lambda s, hr, _r: service.pay_equity(
            s, hr, PayEquityQuery(view=PayEquityView.DEPARTMENTS, country=["DE"])
        ),
    ),
    "pay_equity_cohort": (
        5,
        lambda s, hr, role_id: service.pay_equity_cohort(
            s, hr, CohortQuery(job_role_id=role_id, level=Level.L2, country="DE")
        ),
    ),
    "compare_groups": (
        3,
        lambda s, hr, _r: service.compare_groups(
            s, hr, InsightQuery(country=["DE"]), InsightQuery(country=["IN"]), CompareMetric.MEDIAN
        ),
    ),
}


@pytest.mark.parametrize("name", list(CALLS))
@pytest.mark.usefixtures("frozen_time")
def test_an_insight_runs_the_same_few_queries_for_more_employees(
    db_session: Session, name: str
) -> None:
    budget, call = CALLS[name]
    user = make_user(db_session, role=Role.HR_MANAGER)
    hr = Principal(user_id=user.id, email=user.email, full_name=user.full_name, role=user.role)
    roles = _roles_and_bands(db_session)
    _hire_one_per_cohort(db_session, roles)
    with _counting_selects(db_session) as few:
        call(db_session, hr, roles[0].id)
    for _ in range(3):  # four times the employees, in the same groups
        _hire_one_per_cohort(db_session, roles)

    with _counting_selects(db_session) as more:
        call(db_session, hr, roles[0].id)

    assert len(more) == len(few) <= budget
