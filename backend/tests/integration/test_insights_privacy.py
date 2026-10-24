"""Viewers see aggregates only, never one person's pay (docs/08 section 4, docs/09 section 2.8).

The rules live in the insights service, so the dashboard, exports and Ask all get them:
- the small-group rule: a group of fewer than 5 people has every value and its count hidden;
- `min` and `max` are hidden for every group (each is one person's exact pay);
- complementary suppression: hiding one group of a breakdown hides the next-smallest too;
- a difference between two groups uses the hidden (null) values, so it is hidden too.
"""

from collections.abc import Callable
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import InsightQuery
from salary_api.modules.reference.models import JobRole
from tests.factories import (
    make_department,
    make_employee,
    make_fx_rates,
    make_job_role,
    make_pay_band,
)
from tests.integration.test_authz_matrix import MATRIX, Endpoint

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


def test_viewer_never_sees_min_or_max_even_for_a_large_group(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    _employees(db_session, "DE", 30)

    body = as_role("VIEWER").get(OVERVIEW).json()

    for stats in (body["stats"], body["by_country"][0]["local"], body["by_country"][0]["usd"]):
        assert (stats["count"], stats["min"], stats["max"]) == (30, None, None)
        assert stats["median"] is not None


def _extremes_in(body: object, path: str = "$") -> list[str]:
    """Where a JSON body holds a non-null `min` or `max` of people's pay, at any depth.

    A pay band's min and max are policy, not anyone's pay, so `band` objects are skipped.
    """
    found: list[str] = []
    if isinstance(body, dict):
        for key, value in cast(dict[str, object], body).items():
            if key in ("min", "max") and value is not None:
                found.append(f"{path}.{key}")
            if key != "band":
                found += _extremes_in(value, f"{path}.{key}")
    elif isinstance(body, list):
        for index, value in enumerate(cast(list[object], body)):
            found += _extremes_in(value, f"{path}[{index}]")
    return found


INSIGHT_ROUTES = [row for row in MATRIX if row.path.startswith("/api/v1/insights")]


@pytest.mark.parametrize(
    "endpoint", [pytest.param(row, id=f"{row.method} {row.path}") for row in INSIGHT_ROUTES]
)
def test_viewer_never_receives_a_min_or_max_from_any_insight_endpoint(
    as_role: Callable[[str], TestClient], db_session: Session, endpoint: Endpoint
) -> None:
    _employees(db_session, "DE", 6)
    request = endpoint.prepare(db_session)
    url = request.pop("url", endpoint.path)

    response = as_role("VIEWER").request(endpoint.method, url, **request)

    assert _extremes_in(response.json()) == []


def test_the_extremes_scan_finds_a_min_or_max_but_not_a_band() -> None:
    body = {"groups": [{"stats": {"min": 1, "max": None}, "band": {"min": 2, "max": 3}}]}

    assert _extremes_in(body) == ["$.groups[0].stats.min"]


def _shown_countries(body: dict[str, Any]) -> dict[str, int | None]:
    return {row["country_code"]: row["local"]["count"] for row in body["by_country"]}


@pytest.mark.parametrize(
    ("sizes", "shown"),
    [
        # Hiding Germany alone would let headcount minus the others reveal it: hide France too.
        ({"DE": 3, "FR": 6, "US": 10}, {"DE": None, "FR": None, "US": 10}),
        # Two groups are already hidden, so nothing more is.
        ({"DE": 3, "FR": 2, "US": 10}, {"DE": None, "FR": None, "US": 10}),
        # A tie goes to the group listed first.
        ({"DE": 3, "FR": 6, "GB": 6, "US": 10}, {"DE": None, "FR": None, "GB": 6, "US": 10}),
        # Nothing hidden, nothing more to hide.
        ({"DE": 5, "FR": 6}, {"DE": 5, "FR": 6}),
    ],
)
def test_viewer_has_the_next_smallest_group_hidden_with_a_suppressed_one(
    as_role: Callable[[str], TestClient],
    db_session: Session,
    sizes: dict[str, int],
    shown: dict[str, int | None],
) -> None:
    for country, size in sizes.items():
        _employees(db_session, country, size)

    body = as_role("VIEWER").get(OVERVIEW).json()

    assert _shown_countries(body) == shown
    assert body["headcount"] == sum(sizes.values())  # the total stays visible


def test_hr_has_no_group_hidden_by_complementary_suppression(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    for country, size in {"DE": 3, "FR": 6, "US": 10}.items():
        _employees(db_session, country, size)

    body = as_role("HR_MANAGER").get(OVERVIEW).json()

    assert _shown_countries(body) == {"DE": 3, "FR": 6, "US": 10}


# Cross-endpoint nesting: country > department > job role > level. Every parent whose total
# another endpoint shows under the same filters must have two or more hidden children, or none.


def _hire(session: Session, role: JobRole, count: int, base: int, level: str = "L3") -> None:
    for offset in range(count):
        make_employee(session, job_role=role, level=level, base_minor=base + offset * 100_000)


def _delta_and_echo(session: Session) -> None:
    """Delta: R1 (1 person, the secret) and R2 (6). Echo: R3 (5) and R4 (7). All in DE."""
    roles = {
        title: make_job_role(session, title, department=make_department(session, department))
        for title, department in (("R1", "Delta"), ("R2", "Delta"), ("R3", "Echo"), ("R4", "Echo"))
    }
    _hire(session, roles["R1"], 1, 9_876_543)
    _hire(session, roles["R2"], 6, 5_000_000)
    _hire(session, roles["R3"], 5, 5_000_000)
    _hire(session, roles["R4"], 7, 5_000_000)


@pytest.mark.parametrize("split_by_level", ["false", "true"])
def test_viewer_cannot_recover_a_role_from_its_department_total(
    as_role: Callable[[str], TestClient], db_session: Session, split_by_level: str
) -> None:
    # Department cost shows Delta's total; if R2 were visible, Delta minus R2 would be R1.
    _delta_and_echo(db_session)
    viewer = as_role("VIEWER")

    titles = viewer.get(
        "/api/v1/insights/by-job-title", params={"country": "DE", "split_by_level": split_by_level}
    ).json()
    cost = viewer.get("/api/v1/insights/department-cost", params={"country": "DE"}).json()

    counts = {group["job_role"]["title"]: group["stats"]["count"] for group in titles["groups"]}
    assert counts == {"R1": None, "R2": None, "R3": 5, "R4": 7}
    assert {group["department"]["name"]: group["headcount"] for group in cost["groups"]} == {
        "Delta": 7,
        "Echo": 12,
    }


def _role_r_and_t(session: Session) -> JobRole:
    """In Delta, DE: role R has L2 (1 person, the secret) and L3 (6); role T has L3 (5), L4 (8)."""
    department = make_department(session, "Delta")
    r = make_job_role(session, "R", department=department)
    t = make_job_role(session, "T", department=department)
    for role, level in ((r, "L2"), (r, "L3"), (t, "L3"), (t, "L4")):
        make_pay_band(session, job_role=role, level=level, mid_minor=6_000_000)
    _hire(session, r, 1, 7_654_321, level="L2")
    _hire(session, r, 6, 5_000_000, level="L3")
    _hire(session, t, 5, 5_000_000, level="L3")
    _hire(session, t, 8, 5_000_000, level="L4")
    return r


def test_viewer_cannot_recover_a_level_from_its_role_total(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    # By job title shows R's total; if R L3 were visible, R minus R L3 would be R L2.
    _role_r_and_t(db_session)

    body = (
        as_role("VIEWER")
        .get("/api/v1/insights/by-job-title", params={"country": "DE", "split_by_level": "true"})
        .json()
    )

    counts = [(g["job_role"]["title"], g["level"], g["stats"]["count"]) for g in body["groups"]]
    assert counts == [("R", "L2", None), ("R", "L3", None), ("T", "L3", 5), ("T", "L4", 8)]


@pytest.mark.usefixtures("frozen_time")
def test_viewer_cannot_recover_a_cohort_from_its_role_total(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    # The same attack through pay equity: its cohorts are role x level x country.
    role = _role_r_and_t(db_session)
    viewer = as_role("VIEWER")

    equity = viewer.get("/api/v1/insights/pay-equity", params={"country": "DE"}).json()
    total = viewer.get(
        "/api/v1/insights/by-job-title", params={"country": "DE", "job_role_id": role.id}
    ).json()

    hidden = [(c["job_role"]["title"], c["level"], c["suppressed"]) for c in equity["cohorts"]]
    assert hidden == [("R", "L2", True), ("R", "L3", True), ("T", "L3", False), ("T", "L4", False)]
    assert total["groups"][0]["stats"]["count"] == 7  # the role total is still visible
