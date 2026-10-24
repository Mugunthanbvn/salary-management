"""GET /insights/overview (docs/09-insights-pay-equity.md section 3.1, docs/07 section 8.3)."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import InsightQuery
from tests.factories import make_employee, make_fx_rates

OVERVIEW = "/api/v1/insights/overview"


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, email="caller@acme.example", full_name="Caller", role=role)


def _one_of_each_kind(session: Session) -> None:
    """A full-time, a part-time, a contractor and a terminated full-time employee."""
    make_fx_rates(session)
    make_employee(session, country="DE")
    make_employee(session, country="DE", employment_type="PART_TIME")
    make_employee(session, country="DE", employment_type="CONTRACTOR")
    make_employee(session, country="DE", status="TERMINATED")


def test_overview_counts_only_full_time_active_employees_by_default(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _one_of_each_kind(db_session)

    response = as_role("HR_MANAGER").get(OVERVIEW)

    assert response.status_code == 200
    body = response.json()
    assert body["headcount"] == 1
    assert body["population"] == {
        "country": [],
        "department_id": [],
        "job_role_id": [],
        "level": [],
        "employment_type": ["FULL_TIME"],
        "status": ["ACTIVE"],
        "comp": "base",
    }


def test_overview_population_filters_override_the_defaults(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _one_of_each_kind(db_session)
    params = {"employment_type": ["FULL_TIME", "PART_TIME"], "status": ["ACTIVE", "TERMINATED"]}

    body = as_role("HR_MANAGER").get(OVERVIEW, params=params).json()

    assert body["headcount"] == 3
    assert body["population"]["employment_type"] == ["FULL_TIME", "PART_TIME"]
    assert body["population"]["status"] == ["ACTIVE", "TERMINATED"]


def test_the_insights_service_excludes_part_time_and_contractors_by_default(
    db_session: Session,
) -> None:
    _one_of_each_kind(db_session)

    overview = service.overview(db_session, _principal(Role.HR_MANAGER), InsightQuery())

    assert overview.headcount == 1


def test_overview_refuses_an_unknown_query_parameter(
    as_role: Callable[[str], TestClient],
) -> None:
    response = as_role("HR_MANAGER").get(OVERVIEW, params={"period": "monthly"})

    assert response.status_code == 422
    assert response.json()["type"] == "https://acme.example/problems/validation"
