"""GET /insights/top-earners (docs/09-insights-pay-equity.md section 3.6, docs/07 8.8).

It lists individuals with their pay, so it needs SALARY_READ and every view is audited.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from salary_api.core.errors import Forbidden
from salary_api.core.permissions import Principal, Role
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import TopEarnersQuery
from tests.factories import make_employee, make_job_role

TOP_EARNERS = "/api/v1/insights/top-earners"


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, email="caller@acme.example", full_name="Caller", role=role)


@pytest.fixture
def uk_staff(db_session: Session) -> None:
    """Four full-time UK employees (two tied at £80,000), plus people who never count."""
    for code, base in (
        ("101", 8_000_000),
        ("102", 9_000_000),
        ("103", 8_000_000),
        ("104", 7_000_000),
    ):
        make_employee(db_session, country="GB", employee_code=f"ACME-000{code}", base_minor=base)
    make_employee(db_session, country="GB", employment_type="PART_TIME", base_minor=20_000_000)
    make_employee(db_session, country="GB", status="TERMINATED", base_minor=20_000_000)
    make_employee(db_session, country="DE", base_minor=20_000_000)


def _codes(body: dict[str, Any]) -> list[str]:
    return [item["employee_code"] for item in body["items"]]


@pytest.mark.usefixtures("uk_staff")
def test_hr_sees_the_top_earners_of_a_country_with_names_and_local_pay(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    role = make_job_role(db_session)

    response = as_role("HR_MANAGER").get(TOP_EARNERS, params={"country": "GB", "n": 1})

    assert response.status_code == 200
    body = response.json()
    assert (body["country_code"], body["currency"], body["direction"], body["n"]) == (
        "GB",
        "GBP",
        "top",
        1,
    )
    item = body["items"][0]
    assert item["employee_code"] == "ACME-000102"
    assert item["first_name"] == "Test"
    assert item["last_name"].startswith("Employee ")
    assert item["job_role"] == {"id": role.id, "title": "Software Engineer"}
    assert item["department"] == {"id": role.department_id, "name": "Engineering"}
    assert (item["level"], item["amount"]) == ("L3", {"amount_minor": 9_000_000, "currency": "GBP"})
    assert isinstance(item["employee_id"], int)


@pytest.mark.parametrize(
    ("params", "codes"),
    [
        # Ties are broken by employee code, so the order is always the same.
        ({"n": 3}, ["ACME-000102", "ACME-000101", "ACME-000103"]),
        ({"n": 2, "direction": "bottom"}, ["ACME-000104", "ACME-000101"]),
        ({}, ["ACME-000102", "ACME-000101", "ACME-000103", "ACME-000104"]),  # n defaults to 10
    ],
)
@pytest.mark.usefixtures("uk_staff")
def test_top_earners_rank_full_time_active_employees_by_pay(
    as_role: Callable[[str], TestClient], params: dict[str, Any], codes: list[str]
) -> None:
    body = as_role("HR_MANAGER").get(TOP_EARNERS, params={"country": "GB"} | params).json()

    assert _codes(body) == codes


def test_top_earners_rank_by_total_comp_when_asked(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_employee(db_session, country="GB", employee_code="ACME-000201", base_minor=9_000_000)
    make_employee(
        db_session,
        country="GB",
        employee_code="ACME-000202",
        base_minor=8_000_000,
        components=[("BONUS_TARGET", "Bonus", 2_000_000)],
    )

    body = (
        as_role("HR_MANAGER")
        .get(TOP_EARNERS, params={"country": "GB", "comp": "total", "n": 1})
        .json()
    )

    assert body["items"][0]["amount"] == {"amount_minor": 10_000_000, "currency": "GBP"}


@pytest.mark.parametrize(
    ("params", "field"),
    [({}, "country"), ({"country": "GB", "n": 51}, "n"), ({"country": "GB", "n": 0}, "n")],
)
def test_top_earners_need_a_country_and_at_most_fifty_people(
    as_role: Callable[[str], TestClient], params: dict[str, Any], field: str
) -> None:
    response = as_role("HR_MANAGER").get(TOP_EARNERS, params=params)

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["query", field]


def test_viewer_cannot_see_top_earners(as_role: Callable[[str], TestClient]) -> None:
    response = as_role("VIEWER").get(TOP_EARNERS, params={"country": "GB"})

    assert response.status_code == 403
    assert response.json()["type"] == "https://acme.example/problems/forbidden"


def test_the_service_refuses_top_earners_to_a_caller_without_salary_read(
    db_session: Session,
) -> None:
    with pytest.raises(Forbidden):
        service.top_earners(db_session, _principal(Role.VIEWER), TopEarnersQuery(country="GB"))


def _views(session: Session) -> list[AuditEvent]:
    query = select(AuditEvent).where(AuditEvent.action == "insights.individuals_view")
    return list(session.scalars(query))


@pytest.mark.usefixtures("uk_staff")
def test_viewing_top_earners_writes_one_individuals_view_event_with_the_filters(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    hr = as_role("HR_MANAGER")

    hr.get(TOP_EARNERS, params={"country": "GB", "n": 3, "direction": "bottom"})

    [event] = _views(db_session)
    assert (event.entity, event.entity_id) == ("insights", None)
    assert event.actor_id is not None
    assert event.diff == {
        "endpoint": "top-earners",
        "filters": {
            "country": "GB",
            "n": 3,
            "direction": "bottom",
            "comp": "base",
            "department_id": [],
            "job_role_id": [],
            "level": [],
            "employment_type": ["FULL_TIME"],
            "status": ["ACTIVE"],
        },
    }


def test_a_refused_top_earners_request_writes_no_event(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    as_role("VIEWER").get(TOP_EARNERS, params={"country": "GB"})

    assert _views(db_session) == []
