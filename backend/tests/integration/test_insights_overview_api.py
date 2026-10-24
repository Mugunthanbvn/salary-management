"""GET /insights/overview (docs/09-insights-pay-equity.md section 3.1, docs/07 section 8.3)."""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.domain.money import CurrencyMismatchError, FxRateMissingError
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import InsightQuery
from tests.factories import make_employee, make_fx_rate, make_fx_rates

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


def _stats(currency: str, *values: int | None, suppressed: bool = False) -> dict[str, Any]:
    """A stats object: count, min, p25, median, mean, p75, max (docs/07 section 8.2)."""
    names = ("count", "min", "p25", "median", "mean", "p75", "max")
    return dict(zip(names, values, strict=True)) | {"currency": currency, "suppressed": suppressed}


def _germany_and_india(session: Session) -> None:
    """Five salaries in Germany (EUR) and one in India (INR), whose rate is older."""
    make_fx_rate(session, "INR", as_of=date(2026, 9, 15))
    make_fx_rates(session)
    for base in (5_000_000, 6_000_000, 7_000_000, 8_000_000, 9_000_000):
        make_employee(session, country="DE", base_minor=base)
    make_employee(session, country="IN", base_minor=240_000_000)


def test_overview_converts_each_salary_to_usd_before_mixing_currencies(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _germany_and_india(db_session)

    body = as_role("HR_MANAGER").get(OVERVIEW).json()

    # EUR at 1.085: 5,000,000 cents is 5,425,000 US cents. INR at 0.01198: 240,000,000 paise
    # is 2,875,200 US cents. The org median sits between two German salaries, in USD.
    assert body["currency"] == "USD"
    assert body["fx_as_of"] == "2026-09-15"  # the oldest rate used
    assert body["headcount"] == 6
    assert body["total_payroll_usd"] == {"amount_minor": 40_850_200, "currency": "USD"}
    assert body["stats"] == _stats(
        "USD", 6, 2_875_200, 5_696_250, 7_052_500, 6_808_367, 8_408_750, 9_765_000
    )
    assert body["by_country"] == [
        {
            "country_code": "DE",
            "local": _stats(
                "EUR", 5, 5_000_000, 6_000_000, 7_000_000, 7_000_000, 8_000_000, 9_000_000
            ),
            "usd": _stats(
                "USD", 5, 5_425_000, 6_510_000, 7_595_000, 7_595_000, 8_680_000, 9_765_000
            ),
        },
        {
            "country_code": "IN",
            "local": _stats("INR", 1, *[240_000_000] * 6),
            "usd": _stats("USD", 1, *[2_875_200] * 6),
        },
    ]


def test_overview_of_one_currency_is_in_that_currency(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _germany_and_india(db_session)

    body = as_role("HR_MANAGER").get(OVERVIEW, params={"country": "DE"}).json()

    assert body["currency"] == "EUR"
    assert body["stats"] == _stats(
        "EUR", 5, 5_000_000, 6_000_000, 7_000_000, 7_000_000, 8_000_000, 9_000_000
    )
    assert body["total_payroll_usd"] == {"amount_minor": 37_975_000, "currency": "USD"}
    assert body["fx_as_of"] == "2026-10-01"  # only the EUR rate was used


def test_overview_of_total_comp_uses_base_plus_allowances_and_bonus_target(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rates(db_session)
    make_employee(
        db_session,
        base_minor=6_000_000,
        components=[("ALLOWANCE", "Transport", 60_000), ("BONUS_TARGET", "Bonus", 600_000)],
    )

    body = as_role("HR_MANAGER").get(OVERVIEW, params={"comp": "total", "country": "DE"}).json()

    assert body["stats"] == _stats("EUR", 1, *[6_660_000] * 6)
    assert body["population"]["comp"] == "total"


def test_overview_of_nobody_has_no_amounts(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rates(db_session)

    body = as_role("HR_MANAGER").get(OVERVIEW).json()

    assert body["headcount"] == 0
    assert body["total_payroll_usd"] is None
    assert body["fx_as_of"] is None
    assert body["stats"] == _stats("USD", 0, *[None] * 6)
    assert body["by_country"] == []


def test_a_missing_usd_rate_is_an_explicit_server_error_naming_the_currency(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rate(db_session, "EUR")
    make_employee(db_session, country="DE")
    make_employee(db_session, country="IN")  # no INR rate

    response = as_role("HR_MANAGER").get(OVERVIEW)

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert (body["type"], body["currency"]) == ("about:blank", "INR")
    assert "No USD rate for INR" in body["detail"]


def test_the_service_never_falls_back_to_a_rate_of_zero_or_one(db_session: Session) -> None:
    make_employee(db_session, country="IN")

    with pytest.raises(FxRateMissingError):
        service.overview(db_session, _principal(Role.HR_MANAGER), InsightQuery())


def test_a_missing_rate_of_a_currency_not_in_the_population_does_not_matter(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_fx_rate(db_session, "EUR")
    make_employee(db_session, country="DE")
    make_employee(db_session, country="IN")  # no INR rate, but filtered out

    response = as_role("HR_MANAGER").get(OVERVIEW, params={"country": "DE"})

    assert response.status_code == 200


def test_an_unknown_country_in_the_filter_is_a_validation_error(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    make_employee(db_session, country="DE")

    response = as_role("HR_MANAGER").get(OVERVIEW, params={"country": ["DE", "XX"]})

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"loc": ["query", "country"], "code": "not_found", "message": "Unknown country XX."}
    ]


def _a_german_salary_stored_in_usd(session: Session) -> None:
    """Corrupt data: v1 validates that every salary is in its country's currency."""
    make_fx_rates(session)
    make_employee(session, country="DE")
    make_employee(session, country="DE").currency = "USD"
    session.flush()


def test_a_country_group_never_mixes_two_currencies(db_session: Session) -> None:
    _a_german_salary_stored_in_usd(db_session)

    with pytest.raises(CurrencyMismatchError):
        service.overview(db_session, _principal(Role.HR_MANAGER), InsightQuery(country=["DE"]))


def test_a_local_currency_statistic_never_takes_an_amount_in_another_currency(
    db_session: Session,
) -> None:
    _a_german_salary_stored_in_usd(db_session)

    with pytest.raises(CurrencyMismatchError):
        service.by_department(db_session, _principal(Role.HR_MANAGER), InsightQuery(country=["DE"]))
