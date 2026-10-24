"""Salary ranges and salary sorts compare one currency, or USD (docs/07-api-spec.md 6.1).

Raw minor units of different currencies are never compared: ¥6,000,000 is not more than
€60,000.00 just because 6000000 > 60000.
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.core.schemas import SalaryBasis
from salary_api.domain.money import FxRateMissingError
from salary_api.modules.employees import service
from salary_api.modules.employees.schemas import EmployeeListQuery
from tests.factories import make_employee, make_fx_rate, make_fx_rates

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


@pytest.fixture
def salaries_worth_about_108_500_usd(db_session: Session) -> None:
    make_fx_rates(db_session)  # EUR 1.085, JPY 0.0067, INR 0.01198
    make_employee(db_session, country="US", base_minor=10_850_000, last_name="Dollar")
    make_employee(db_session, country="DE", base_minor=10_000_000, last_name="Euro")
    make_employee(db_session, country="DE", base_minor=9_999_999, last_name="Euro cent less")
    make_employee(db_session, country="JP", base_minor=16_194_030, last_name="Yen")
    make_employee(db_session, country="IN", base_minor=500_000_000, last_name="Rupee")


@pytest.mark.parametrize(
    ("bounds", "last_names"),
    [
        ({"salary_min": 10_850_000}, ["Dollar", "Euro", "Yen"]),
        ({"salary_max": 10_849_999}, ["Euro cent less", "Rupee"]),
        ({"salary_min": 5_990_000, "salary_max": 5_990_000}, ["Rupee"]),
    ],
)
@pytest.mark.usefixtures("salaries_worth_about_108_500_usd")
def test_a_usd_salary_range_compares_every_currency_by_its_usd_value(
    as_role: Callable[[str], TestClient], bounds: dict[str, int], last_names: list[str]
) -> None:
    # $108,500.00 = €100,000.00 = ¥16,194,030 (half-even to the cent); ₹5,000,000 = $59,900
    response = as_role("HR_MANAGER").get(EMPLOYEES, params=bounds | {"salary_basis": "usd"})

    assert response.status_code == 200
    assert _last_names(response.json()) == last_names


def test_a_usd_range_needs_only_the_rates_of_the_currencies_asked_for(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rate(db_session, "EUR")
    make_employee(db_session, country="DE", base_minor=10_000_000, last_name="Euro")

    response = as_role("HR_MANAGER").get(
        EMPLOYEES, params={"currency": "EUR", "salary_basis": "usd", "salary_min": 10_850_000}
    )

    assert _last_names(response.json()) == ["Euro"]


def test_a_usd_range_without_a_needed_rate_is_a_configuration_error(db_session: Session) -> None:
    make_fx_rate(db_session, "EUR")
    hr = Principal(user_id=1, email="hr@acme.example", full_name="HR", role=Role.HR_MANAGER)
    query = EmployeeListQuery(salary_basis=SalaryBasis.USD, salary_min=1)

    with pytest.raises(FxRateMissingError):
        service.list_employees(db_session, hr, query)


@pytest.mark.parametrize(
    ("sort", "last_names"),
    [
        # ¥16,194,030 is $108,500.0001 before rounding, so it sorts just above $108,500.00.
        ("-current_base", ["Yen", "Dollar", "Euro", "Euro cent less", "Rupee"]),
        ("current_base", ["Rupee", "Euro cent less", "Dollar", "Euro", "Yen"]),
    ],
)
@pytest.mark.usefixtures("salaries_worth_about_108_500_usd")
def test_a_usd_salary_sort_orders_every_currency_by_its_usd_value(
    as_role: Callable[[str], TestClient], sort: str, last_names: list[str]
) -> None:
    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"salary_basis": "usd", "sort": sort})

    assert response.status_code == 200
    assert _last_names(response.json()) == last_names


def test_a_usd_sort_on_total_uses_total_compensation(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rates(db_session)
    make_employee(db_session, country="US", base_minor=9_000_000, last_name="Base only")
    make_employee(
        db_session,
        country="DE",
        base_minor=8_000_000,
        components=[("BONUS_TARGET", "Target bonus", 1_000_000)],
        last_name="With bonus",
    )  # €90,000.00 total = $97,650.00

    response = as_role("HR_MANAGER").get(
        EMPLOYEES, params={"salary_basis": "usd", "sort": "-current_total"}
    )

    assert _last_names(response.json()) == ["With bonus", "Base only"]


def test_salary_basis_alone_compares_nothing_and_needs_no_rates(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_employee(db_session, country="DE", last_name="Euro")  # no fx_rates rows at all

    response = as_role("HR_MANAGER").get(EMPLOYEES, params={"salary_basis": "usd"})

    assert response.status_code == 200
    assert _last_names(response.json()) == ["Euro"]
