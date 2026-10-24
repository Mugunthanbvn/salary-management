"""Viewers see aggregates only, never one person's pay (docs/08 section 4, docs/09 section 2.8).

The rules live in the insights service, so the dashboard, exports and Ask all get them:
- the small-group rule: a group of fewer than 5 people has every value and its count hidden;
- `min` and `max` are hidden for every group (each is one person's exact pay);
- complementary suppression: hiding one group of a breakdown hides the next-smallest too;
- a difference between two groups uses the hidden (null) values, so it is hidden too.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import InsightQuery
from tests.factories import make_employee, make_fx_rates

OVERVIEW = "/api/v1/insights/overview"


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, email="caller@acme.example", full_name="Caller", role=role)


def _hidden(currency: str) -> dict[str, Any]:
    """A suppressed stats object: every value and the count are null."""
    values = dict.fromkeys(("count", "min", "p25", "median", "mean", "p75", "max"))
    return values | {"currency": currency, "suppressed": True}


def _employees(session: Session, country: str, count: int, base_minor: int = 6_000_000) -> None:
    for offset in range(count):
        make_employee(session, country=country, base_minor=base_minor + offset * 100_000)


@pytest.fixture(autouse=True)
def _rates(db_session: Session) -> None:
    make_fx_rates(db_session)


def test_viewer_sees_a_group_of_four_suppressed_with_its_count_hidden(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _employees(db_session, "DE", 4)

    body = as_role("VIEWER").get(OVERVIEW, params={"country": "DE"}).json()

    assert body["headcount"] is None
    assert body["total_payroll_usd"] is None
    assert body["stats"] == _hidden("EUR")
    assert body["by_country"] == [
        {"country_code": "DE", "local": _hidden("EUR"), "usd": _hidden("USD")}
    ]


def test_viewer_sees_a_group_of_five(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _employees(db_session, "DE", 5)

    body = as_role("VIEWER").get(OVERVIEW, params={"country": "DE"}).json()

    assert body["headcount"] == 5
    assert (body["stats"]["count"], body["stats"]["median"]) == (5, 6_200_000)
    assert body["stats"]["suppressed"] is False


@pytest.mark.parametrize("role", ["HR_MANAGER", "ADMIN"])
def test_callers_with_salary_read_see_small_groups(
    as_role: Callable[[str], TestClient], db_session: Session, role: str
) -> None:
    _employees(db_session, "DE", 4)

    body = as_role(role).get(OVERVIEW, params={"country": "DE"}).json()

    assert body["headcount"] == 4
    assert body["stats"]["suppressed"] is False


def test_the_service_applies_the_small_group_rule_itself(db_session: Session) -> None:
    _employees(db_session, "DE", 4)

    overview = service.overview(db_session, _principal(Role.VIEWER), InsightQuery(country=["DE"]))

    assert (overview.headcount, overview.stats.count, overview.stats.suppressed) == (
        None,
        None,
        True,
    )
