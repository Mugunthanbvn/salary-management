"""Pay by department and by job title (docs/09 sections 3.2-3.3, docs/07 sections 8.4-8.5)."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import JobFamily, JobRole
from tests.factories import make_department, make_employee, make_fx_rates, make_job_role

BY_DEPARTMENT = "/api/v1/insights/by-department"


def _stats(currency: str, *values: int | None, suppressed: bool = False) -> dict[str, Any]:
    """A stats object: count, min, p25, median, mean, p75, max (docs/07 section 8.2)."""
    names = ("count", "min", "p25", "median", "mean", "p75", "max")
    return dict(zip(names, values, strict=True)) | {"currency": currency, "suppressed": suppressed}


def _role(session: Session, title: str, department: str) -> JobRole:
    return make_job_role(
        session, title, department=make_department(session, department), family=JobFamily.SALES
    )


@pytest.fixture(autouse=True)
def _rates(db_session: Session) -> None:
    make_fx_rates(db_session)


def test_pay_by_department_in_one_country_is_in_local_currency(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    engineer = make_job_role(db_session, "Software Engineer")
    seller = _role(db_session, "Account Executive", "Sales")
    make_employee(db_session, country="DE", job_role=engineer, base_minor=5_000_000)
    make_employee(db_session, country="DE", job_role=engineer, base_minor=7_000_000)
    make_employee(db_session, country="DE", job_role=seller, base_minor=4_000_000)
    make_employee(db_session, country="IN", job_role=seller, base_minor=240_000_000)

    response = as_role("HR_MANAGER").get(BY_DEPARTMENT, params={"country": "DE"})

    assert response.status_code == 200
    body = response.json()
    assert (body["currency"], body["fx_as_of"]) == ("EUR", None)
    assert body["population"]["country"] == ["DE"]
    assert body["groups"] == [
        {
            "department": {"id": engineer.department_id, "name": "Engineering"},
            "stats": _stats(
                "EUR", 2, 5_000_000, 5_500_000, 6_000_000, 6_000_000, 6_500_000, 7_000_000
            ),
        },
        {
            "department": {"id": seller.department_id, "name": "Sales"},
            "stats": _stats("EUR", 1, *[4_000_000] * 6),
        },
    ]


def test_pay_by_department_across_countries_converts_each_salary_to_usd(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    engineer = make_job_role(db_session, "Software Engineer")
    make_employee(db_session, country="DE", job_role=engineer, base_minor=5_000_000)
    make_employee(db_session, country="IN", job_role=engineer, base_minor=240_000_000)

    body = as_role("HR_MANAGER").get(BY_DEPARTMENT).json()

    # 5,000,000 EUR cents is 5,425,000 US cents; 240,000,000 paise is 2,875,200 US cents.
    assert (body["currency"], body["fx_as_of"]) == ("USD", "2026-10-01")
    assert body["groups"][0]["stats"] == _stats(
        "USD", 2, 2_875_200, 3_512_650, 4_150_100, 4_150_100, 4_787_550, 5_425_000
    )


def test_pay_by_department_follows_the_department_filter(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    engineer = make_job_role(db_session, "Software Engineer")
    seller = _role(db_session, "Account Executive", "Sales")
    make_employee(db_session, job_role=engineer)
    make_employee(db_session, job_role=seller)

    body = (
        as_role("HR_MANAGER")
        .get(BY_DEPARTMENT, params={"department_id": seller.department_id})
        .json()
    )

    assert [group["department"]["name"] for group in body["groups"]] == ["Sales"]


def test_viewer_sees_small_departments_hidden_with_their_complement(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    sizes = {"Customer Success": 3, "Engineering": 6, "Sales": 10}
    for department, size in sizes.items():
        role = _role(db_session, f"{department} role", department)
        for _ in range(size):
            make_employee(db_session, country="DE", job_role=role)

    body = as_role("VIEWER").get(BY_DEPARTMENT, params={"country": "DE"}).json()

    counts = {group["department"]["name"]: group["stats"]["count"] for group in body["groups"]}
    assert counts == {"Customer Success": None, "Engineering": None, "Sales": 10}
    assert body["groups"][0]["stats"]["suppressed"] is True
