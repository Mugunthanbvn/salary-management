"""Salary ranges and salary sorts compare one currency, or USD (docs/07-api-spec.md 6.1).

Raw minor units of different currencies are never compared: ¥6,000,000 is not more than
€60,000.00 just because 6000000 > 60000.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_employee

EMPLOYEES = "/api/v1/employees"
PROBLEMS = "https://acme.example/problems/"


def _last_names(response_json: dict[str, list[dict[str, str]]]) -> list[str]:
    return [item["last_name"] for item in response_json["items"]]


@pytest.fixture
def euro_salaries(db_session: Session) -> None:
    make_employee(db_session, country="DE", base_minor=4_000_000, last_name="Low")
    make_employee(db_session, country="DE", base_minor=6_000_000, last_name="Mid")
    make_employee(db_session, country="FR", base_minor=8_000_000, last_name="High")
    # Same number of minor units, another currency: never part of a EUR range.
    make_employee(db_session, country="US", base_minor=6_000_000, last_name="Dollar")


@pytest.mark.usefixtures("euro_salaries")
def test_a_salary_range_in_one_currency_includes_both_bounds(
    as_role: Callable[[str], TestClient],
) -> None:
    params = {"currency": "EUR", "salary_min": 6_000_000, "salary_max": 8_000_000}

    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params)

    assert response.status_code == 200
    assert _last_names(response.json()) == ["High", "Mid"]


@pytest.mark.usefixtures("euro_salaries")
def test_one_country_fixes_the_currency_of_a_salary_range(
    as_role: Callable[[str], TestClient],
) -> None:
    response = as_role("HR_MANAGER").get(
        EMPLOYEES, params={"country": "DE", "salary_min": 5_000_000}
    )

    assert _last_names(response.json()) == ["Mid"]


@pytest.mark.parametrize(("comp", "last_names"), [("base", []), ("total", ["Bonus"])])
def test_comp_chooses_base_or_total_for_the_salary_range(
    as_role: Callable[[str], TestClient], db_session: Session, comp: str, last_names: list[str]
) -> None:
    make_employee(
        db_session,
        country="DE",
        base_minor=5_000_000,
        components=[("BONUS_TARGET", "Target bonus", 2_000_000)],
        last_name="Bonus",
    )

    response = as_role("HR_MANAGER").get(
        EMPLOYEES, params={"currency": "EUR", "salary_min": 6_500_000, "comp": comp}
    )

    assert _last_names(response.json()) == last_names


@pytest.mark.parametrize(
    ("params", "loc"),
    [
        ({"salary_min": 1}, "salary_min"),
        ({"salary_max": 1, "currency": ["EUR", "USD"]}, "salary_max"),
        ({"salary_min": 1, "salary_basis": "local", "country": ["DE", "US"]}, "salary_min"),
        ({"sort": "current_base"}, "sort"),
        ({"sort": "-current_total", "country": ["DE", "FR"]}, "sort"),
    ],
)
def test_a_salary_range_or_sort_that_could_mix_currencies_is_refused(
    as_role: Callable[[str], TestClient], params: dict[str, str | int | list[str]], loc: str
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params=params)

    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert (error["loc"], error["code"]) == (["query", loc], "currency_required")
    assert "salary_basis=usd" in error["message"]


def test_a_salary_range_whose_minimum_is_above_its_maximum_is_refused(
    as_role: Callable[[str], TestClient],
) -> None:
    response = as_role("HR_MANAGER").get(
        EMPLOYEES, params={"currency": "EUR", "salary_min": 2, "salary_max": 1}
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["query", "salary_min"]


@pytest.mark.usefixtures("euro_salaries")
def test_a_salary_sort_in_one_currency_orders_by_amount(
    as_role: Callable[[str], TestClient],
) -> None:
    response = as_role("HR_MANAGER").get(
        EMPLOYEES, params={"currency": "EUR", "sort": "-current_base"}
    )

    assert _last_names(response.json()) == ["High", "Mid", "Low"]
