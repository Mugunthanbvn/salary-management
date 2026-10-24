"""GET /insights/department-cost (docs/09-insights-pay-equity.md section 3.5, docs/07 8.7)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import JobFamily, JobRole
from tests.factories import make_department, make_employee, make_fx_rates, make_job_role

DEPARTMENT_COST = "/api/v1/insights/department-cost"


def _usd(amount_minor: int) -> dict[str, int | str]:
    return {"amount_minor": amount_minor, "currency": "USD"}


def _eur(amount_minor: int) -> dict[str, int | str]:
    return {"amount_minor": amount_minor, "currency": "EUR"}


def _role(session: Session, title: str, department: str) -> JobRole:
    return make_job_role(
        session, title, department=make_department(session, department), family=JobFamily.SALES
    )


@pytest.fixture(autouse=True)
def _rates(db_session: Session) -> None:
    make_fx_rates(db_session)


def test_department_cost_across_countries_sums_each_salary_in_usd(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    engineer = make_job_role(db_session, "Software Engineer")
    seller = _role(db_session, "Account Executive", "Sales")
    make_employee(db_session, country="DE", job_role=engineer, base_minor=5_000_000)
    make_employee(db_session, country="IN", job_role=engineer, base_minor=240_000_000)
    make_employee(db_session, country="DE", job_role=seller, base_minor=4_000_000)

    response = as_role("HR_MANAGER").get(DEPARTMENT_COST)

    assert response.status_code == 200
    body = response.json()
    # 5,425,000 + 2,875,200 US cents for Engineering; 4,340,000 for Sales.
    assert (body["currency"], body["fx_as_of"], body["headcount"]) == ("USD", "2026-10-01", 3)
    assert (body["total"], body["total_usd"]) == (_usd(12_640_200), _usd(12_640_200))
    assert body["groups"] == [
        {
            "department": {"id": engineer.department_id, "name": "Engineering"},
            "headcount": 2,
            "cost": _usd(8_300_200),
            "cost_usd": _usd(8_300_200),
            "share_of_total": "0.6567",
            "suppressed": False,
        },
        {
            "department": {"id": seller.department_id, "name": "Sales"},
            "headcount": 1,
            "cost": _usd(4_340_000),
            "cost_usd": _usd(4_340_000),
            "share_of_total": "0.3433",
            "suppressed": False,
        },
    ]


def test_department_cost_in_one_country_is_local_with_a_usd_equivalent(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    engineer = make_job_role(db_session, "Software Engineer")
    seller = _role(db_session, "Account Executive", "Sales")
    make_employee(db_session, country="DE", job_role=engineer, base_minor=5_000_000)
    make_employee(db_session, country="DE", job_role=engineer, base_minor=7_000_000)
    make_employee(db_session, country="DE", job_role=seller, base_minor=4_000_000)

    body = as_role("HR_MANAGER").get(DEPARTMENT_COST, params={"country": "DE"}).json()

    assert body["currency"] == "EUR"
    assert (body["total"], body["total_usd"]) == (_eur(16_000_000), _usd(17_360_000))
    assert [
        (group["cost"], group["cost_usd"], group["share_of_total"]) for group in body["groups"]
    ] == [
        (_eur(12_000_000), _usd(13_020_000), "0.7500"),
        (_eur(4_000_000), _usd(4_340_000), "0.2500"),
    ]


def test_viewer_gets_no_cost_or_share_for_a_hidden_department(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    for department, size in {"Customer Success": 3, "Engineering": 6, "Sales": 10}.items():
        role = _role(db_session, f"{department} role", department)
        for _ in range(size):
            make_employee(db_session, country="DE", job_role=role, base_minor=6_000_000)

    body = as_role("VIEWER").get(DEPARTMENT_COST, params={"country": "DE"}).json()

    # The share is computed from the hidden cost, so it is hidden too (privacy rule b);
    # Engineering is hidden as Customer Success's complement (rule c).
    hidden = {"headcount": None, "cost": None, "cost_usd": None, "share_of_total": None}
    assert [{key: group[key] for key in hidden} for group in body["groups"]] == [
        hidden,
        hidden,
        {
            "headcount": 10,
            "cost": _eur(60_000_000),
            "cost_usd": _usd(65_100_000),
            "share_of_total": "0.5263",
        },
    ]
    assert [group["suppressed"] for group in body["groups"]] == [True, True, False]
    assert (body["headcount"], body["total"]) == (19, _eur(114_000_000))


def test_viewer_gets_no_total_for_a_population_under_five(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    for _ in range(4):
        make_employee(db_session, country="DE")

    body = as_role("VIEWER").get(DEPARTMENT_COST, params={"country": "DE"}).json()

    assert (body["headcount"], body["total"], body["total_usd"], body["suppressed"]) == (
        None,
        None,
        None,
        True,
    )
    assert body["groups"][0]["share_of_total"] is None
