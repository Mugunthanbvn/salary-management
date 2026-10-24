"""GET /insights/pay-equity (docs/09-insights-pay-equity.md section 3.8, docs/07 8.10).

Compa-ratio = base pay / the midpoint of the pay band for the same role, level and country.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import JobFamily, JobRole
from tests.factories import (
    make_country,
    make_department,
    make_employee,
    make_job_role,
    make_pay_band,
)

PAY_EQUITY = "/api/v1/insights/pay-equity"

# Base pay against a band midpoint of EUR 50,000: 0.78, 0.92, 0.96, 1.00 and 1.22.
CSM_BASES = (3_900_000, 4_600_000, 4_800_000, 5_000_000, 6_100_000)


def _csm(session: Session) -> JobRole:
    return make_job_role(
        session,
        "Customer Success Manager",
        department=make_department(session, "Customer Success"),
        family=JobFamily.CUSTOMER_SUCCESS,
    )


@pytest.fixture
def germany(db_session: Session) -> tuple[JobRole, JobRole]:
    """Five Customer Success Managers (L2) and two engineers, one of them without a band."""
    csm = _csm(db_session)
    engineer = make_job_role(db_session, "Software Engineer")
    make_pay_band(db_session, job_role=csm, level="L2", country="DE", mid_minor=5_000_000)
    make_pay_band(db_session, job_role=engineer, level="L3", country="DE", mid_minor=6_000_000)
    for base in CSM_BASES:
        make_employee(db_session, country="DE", job_role=csm, level="L2", base_minor=base)
    make_employee(db_session, country="DE", job_role=engineer, level="L3", base_minor=6_000_000)
    make_employee(db_session, country="DE", job_role=engineer, level="L5", base_minor=9_000_000)
    return csm, engineer


@pytest.mark.usefixtures("frozen_time")
def test_hr_sees_each_cohort_against_its_band(
    as_role: Callable[[str], TestClient], germany: tuple[JobRole, JobRole]
) -> None:
    csm, _engineer = germany

    response = as_role("HR_MANAGER").get(PAY_EQUITY)

    assert response.status_code == 200
    body = response.json()
    assert body["view"] == "cohorts"
    assert body["thresholds"] == {"low": "0.80", "high": "1.20", "rollup": "0.95"}
    assert body["cohorts"][0] == {
        "job_role": {"id": csm.id, "title": "Customer Success Manager"},
        "level": "L2",
        "country_code": "DE",
        "department": {"id": csm.department_id, "name": "Customer Success"},
        "stats": {
            "count": 5,
            "min": 3_900_000,
            "p25": 4_600_000,
            "median": 4_800_000,
            "mean": 4_880_000,
            "p75": 5_000_000,
            "max": 6_100_000,
            "currency": "EUR",
            "suppressed": False,
        },
        "band": {"min": 4_000_000, "mid": 5_000_000, "max": 6_000_000, "currency": "EUR"},
        "median_compa_ratio": "0.96",
        "underpaid_count": 1,
        "overpaid_count": 1,
        "suppressed": False,
    }
    assert [cohort["job_role"]["title"] for cohort in body["cohorts"]] == [
        "Customer Success Manager",
        "Software Engineer",
    ]
    assert body["summary"] == {
        "employees_evaluated": 6,
        "employees_without_band": 1,  # the L5 engineer
        "employees_not_full_time": 0,
        "employees_flagged_underpaid": 1,
        "employees_flagged_overpaid": 1,
        "suppressed": False,
    }


@pytest.mark.usefixtures("frozen_time", "germany")
def test_viewer_sees_a_small_cohort_suppressed_but_its_band_visible(
    as_role: Callable[[str], TestClient],
) -> None:
    body = as_role("VIEWER").get(PAY_EQUITY).json()

    # The engineer cohort (1 person) is hidden, and so is its complement, the CSM cohort.
    for cohort in body["cohorts"]:
        assert cohort["suppressed"] is True
        assert cohort["stats"]["count"] is None
        assert (cohort["median_compa_ratio"], cohort["underpaid_count"]) == (None, None)
        assert cohort["overpaid_count"] is None
        assert cohort["band"]["mid"] is not None
    assert body["summary"]["employees_evaluated"] == 6


def test_viewer_sees_a_cohort_of_five_with_its_ratios(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    csm = _csm(db_session)
    make_pay_band(db_session, job_role=csm, level="L2", mid_minor=5_000_000)
    for base in CSM_BASES:
        make_employee(db_session, job_role=csm, level="L2", base_minor=base)

    [cohort] = as_role("VIEWER").get(PAY_EQUITY).json()["cohorts"]

    assert (cohort["suppressed"], cohort["median_compa_ratio"]) == (False, "0.96")
    assert (cohort["stats"]["min"], cohort["stats"]["max"]) == (None, None)


@pytest.mark.usefixtures("frozen_time", "germany")
def test_part_timers_in_the_population_get_no_compa_ratio(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    csm = _csm(db_session)
    # Paid half the band: as a full-timer this would be flagged underpaid.
    make_employee(
        db_session,
        country="DE",
        job_role=csm,
        level="L2",
        employment_type="PART_TIME",
        base_minor=2_500_000,
    )

    body = (
        as_role("HR_MANAGER")
        .get(PAY_EQUITY, params={"employment_type": ["FULL_TIME", "PART_TIME"]})
        .json()
    )

    assert body["population"]["employment_type"] == ["FULL_TIME", "PART_TIME"]
    assert body["summary"]["employees_not_full_time"] == 1
    assert body["summary"]["employees_flagged_underpaid"] == 1  # still only the 0.78
    assert (body["cohorts"][0]["stats"]["count"], body["cohorts"][0]["underpaid_count"]) == (5, 1)


def test_pay_equity_refuses_comp_because_bands_are_base_pay(
    as_role: Callable[[str], TestClient],
) -> None:
    response = as_role("HR_MANAGER").get(PAY_EQUITY, params={"comp": "total"})

    assert response.status_code == 422


@pytest.mark.usefixtures("frozen_time")
def test_the_band_in_force_today_is_the_latest_one_already_started(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    csm = _csm(db_session)
    for effective_from, mid in (
        (date(2025, 1, 1), 4_000_000),
        (date(2026, 1, 1), 5_000_000),
        (date(2027, 1, 1), 9_000_000),  # not started yet (today is 2026-10-01)
    ):
        make_pay_band(
            db_session, job_role=csm, level="L2", mid_minor=mid, effective_from=effective_from
        )
    make_employee(db_session, job_role=csm, level="L2", base_minor=5_000_000)

    [cohort] = as_role("HR_MANAGER").get(PAY_EQUITY).json()["cohorts"]

    assert cohort["band"]["mid"] == 5_000_000
    assert cohort["median_compa_ratio"] == "1.00"


def _cohort_keys(body: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [
        (cohort["job_role"]["title"], cohort["level"], cohort["country_code"])
        for cohort in body["cohorts"]
    ]


@pytest.mark.usefixtures("frozen_time", "germany")
def test_pay_equity_follows_the_population_filters(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    csm = _csm(db_session)
    make_pay_band(db_session, job_role=csm, level="L2", country="FR", mid_minor=5_000_000)
    make_employee(db_session, country="FR", job_role=csm, level="L2", base_minor=5_000_000)

    body = as_role("HR_MANAGER").get(PAY_EQUITY, params={"country": "FR"}).json()

    assert _cohort_keys(body) == [("Customer Success Manager", "L2", "FR")]


@pytest.fixture
def departments_in_germany(db_session: Session) -> tuple[JobRole, JobRole]:
    """Customer Success paid about 8 % under band; Engineering on band, one person over."""
    csm = _csm(db_session)
    engineer = make_job_role(db_session, "Software Engineer")
    make_pay_band(db_session, job_role=csm, level="L2", mid_minor=5_000_000)
    make_pay_band(db_session, job_role=engineer, level="L3", mid_minor=6_000_000)
    # Ratios 0.78, 0.90, 0.92, 0.92, 0.93, 0.94.
    for base in (3_900_000, 4_500_000, 4_600_000, 4_600_000, 4_650_000, 4_700_000):
        make_employee(db_session, job_role=csm, level="L2", base_minor=base)
    # Ratios 0.95, 1.00, 1.00, 1.05, 1.25.
    for base in (5_700_000, 6_000_000, 6_000_000, 6_300_000, 7_500_000):
        make_employee(db_session, job_role=engineer, level="L3", base_minor=base)
    make_pay_band(db_session, job_role=csm, level="L2", country="FR", mid_minor=5_000_000)
    make_employee(db_session, country="FR", job_role=csm, level="L2", base_minor=5_000_000)
    return csm, engineer


@pytest.mark.usefixtures("frozen_time")
def test_the_department_view_shows_a_team_paid_below_band(
    as_role: Callable[[str], TestClient], departments_in_germany: tuple[JobRole, JobRole]
) -> None:
    csm, engineer = departments_in_germany

    response = as_role("HR_MANAGER").get(
        PAY_EQUITY, params={"view": "departments", "country": "DE"}
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["view"], body["country_code"]) == ("departments", "DE")
    assert body["groups"] == [
        {
            "department": {"id": csm.department_id, "name": "Customer Success"},
            "count": 6,
            "median_compa_ratio": "0.92",
            "mean_compa_ratio": "0.90",
            "pct_below_band": "0.17",
            "underpaid_count": 1,
            "overpaid_count": 0,
            "below_threshold": True,
            "suppressed": False,
        },
        {
            "department": {"id": engineer.department_id, "name": "Engineering"},
            "count": 5,
            "median_compa_ratio": "1.00",
            "mean_compa_ratio": "1.05",
            "pct_below_band": "0.00",
            "underpaid_count": 0,
            "overpaid_count": 1,
            "below_threshold": False,
            "suppressed": False,
        },
    ]
    assert body["summary"]["employees_evaluated"] == 11  # France is not in the view


@pytest.mark.parametrize("countries", [[], ["DE", "FR"]])
def test_the_department_view_needs_exactly_one_country(
    as_role: Callable[[str], TestClient], db_session: Session, countries: list[str]
) -> None:
    make_country(db_session, "DE")
    make_country(db_session, "FR")

    response = as_role("HR_MANAGER").get(
        PAY_EQUITY, params={"view": "departments", "country": countries}
    )

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {
            "loc": ["query", "country"],
            "code": "required",
            "message": "The departments view compares departments within one country: "
            "give exactly one country.",
        }
    ]


@pytest.mark.usefixtures("frozen_time")
def test_viewer_sees_a_small_department_hidden_with_its_complement(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    sizes = {"Customer Success": 3, "Engineering": 6, "Sales": 10}
    for department, size in sizes.items():
        role = make_job_role(
            db_session,
            f"{department} role",
            department=make_department(db_session, department),
            family=JobFamily.SALES,
        )
        make_pay_band(db_session, job_role=role, level="L3", mid_minor=6_000_000)
        for _ in range(size):
            make_employee(db_session, job_role=role, level="L3", base_minor=6_000_000)

    body = as_role("VIEWER").get(PAY_EQUITY, params={"view": "departments", "country": "DE"}).json()

    hidden = {
        "count": None,
        "median_compa_ratio": None,
        "mean_compa_ratio": None,
        "pct_below_band": None,
        "underpaid_count": None,
        "overpaid_count": None,
        "below_threshold": None,
        "suppressed": True,
    }
    shown = [{key: group[key] for key in hidden} for group in body["groups"]]
    assert shown[:2] == [hidden, hidden]
    assert (shown[2]["count"], shown[2]["median_compa_ratio"]) == (10, "1.00")


@pytest.mark.usefixtures("frozen_time")
def test_viewer_has_cohorts_hidden_in_pairs_within_each_department(
    as_role: Callable[[str], TestClient], db_session: Session
) -> None:
    # Each department's total is visible in the department view, so one small cohort per
    # department would be revealed by the total minus its other cohort.
    for title, department in (("Customer Success Manager", "Customer Success"), ("SE", "Eng")):
        role = make_job_role(
            db_session,
            title,
            department=make_department(db_session, department),
            family=JobFamily.SALES,
        )
        for level, size in (("L2", 3), ("L3", 10)):
            make_pay_band(db_session, job_role=role, level=level, mid_minor=5_000_000)
            for _ in range(size):
                make_employee(db_session, job_role=role, level=level, base_minor=5_000_000)

    body = as_role("VIEWER").get(PAY_EQUITY).json()

    assert [cohort["suppressed"] for cohort in body["cohorts"]] == [True, True, True, True]
