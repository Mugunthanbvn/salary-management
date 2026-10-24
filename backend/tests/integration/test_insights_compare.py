"""Comparing two populations: the service behind the Ask `compare_groups` tool (docs/10 4).

The service returns the difference itself, so the model never does arithmetic. Privacy rule
(b) of docs/18 B6: the difference is computed from the values after suppression, so it is
null whenever either side is hidden from the caller.
"""

import pytest
from sqlalchemy.orm import Session

from salary_api.core.permissions import Principal, Role
from salary_api.domain.enums import Level
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import CompareMetric, InsightQuery
from tests.factories import make_employee, make_fx_rates


def _principal(role: Role) -> Principal:
    return Principal(user_id=1, email="caller@acme.example", full_name="Caller", role=role)


def _employees(session: Session, country: str, *bases: int) -> None:
    for base in bases:
        make_employee(session, country=country, base_minor=base)


@pytest.fixture(autouse=True)
def _rates(db_session: Session) -> None:
    make_fx_rates(db_session)


def test_comparing_two_populations_in_one_currency_stays_in_that_currency(
    db_session: Session,
) -> None:
    _employees(db_session, "DE", 5_000_000, 6_000_000, 7_000_000)
    _employees(db_session, "FR", 4_000_000, 5_000_000, 6_000_000)

    comparison = service.compare_groups(
        db_session,
        _principal(Role.HR_MANAGER),
        InsightQuery(country=["DE"]),
        InsightQuery(country=["FR"]),
        CompareMetric.MEDIAN,
    )

    assert (comparison.currency, comparison.fx_as_of) == ("EUR", None)
    assert (comparison.a, comparison.b, comparison.difference) == (6_000_000, 5_000_000, 1_000_000)
    assert comparison.pct_difference == "0.2000"  # a is 20 % above b


def test_comparing_populations_in_two_currencies_converts_both_to_usd(
    db_session: Session,
) -> None:
    _employees(db_session, "DE", 5_000_000)  # 5,425,000 US cents
    _employees(db_session, "IN", 240_000_000)  # 2,875,200 US cents

    comparison = service.compare_groups(
        db_session,
        _principal(Role.HR_MANAGER),
        InsightQuery(country=["DE"]),
        InsightQuery(country=["IN"]),
        CompareMetric.MEAN,
    )

    assert (comparison.currency, comparison.fx_as_of is not None) == ("USD", True)
    assert (comparison.a, comparison.b, comparison.difference) == (
        5_425_000,
        2_875_200,
        2_549_800,
    )


@pytest.mark.parametrize(
    ("metric", "values", "currency"),
    [
        (CompareMetric.HEADCOUNT, (3, 2, 1), None),
        (CompareMetric.TOTAL_COST, (18_000_000, 9_000_000, 9_000_000), "EUR"),
    ],
)
def test_headcount_and_total_cost_can_be_compared(
    db_session: Session,
    metric: CompareMetric,
    values: tuple[int, int, int],
    currency: str | None,
) -> None:
    _employees(db_session, "DE", 5_000_000, 6_000_000, 7_000_000)
    _employees(db_session, "FR", 4_000_000, 5_000_000)

    comparison = service.compare_groups(
        db_session,
        _principal(Role.HR_MANAGER),
        InsightQuery(country=["DE"]),
        InsightQuery(country=["FR"]),
        metric,
    )

    assert (comparison.a, comparison.b, comparison.difference) == values
    assert comparison.currency == currency


def test_viewer_gets_no_difference_when_either_side_is_hidden(db_session: Session) -> None:
    _employees(db_session, "DE", *[6_000_000] * 3)  # under 5: hidden
    _employees(db_session, "FR", *[5_000_000] * 10)

    comparison = service.compare_groups(
        db_session,
        _principal(Role.VIEWER),
        InsightQuery(country=["DE"]),
        InsightQuery(country=["FR"]),
        CompareMetric.MEDIAN,
    )

    assert (comparison.a, comparison.a_suppressed) == (None, True)
    assert (comparison.b, comparison.b_suppressed) == (5_000_000, False)
    assert (comparison.difference, comparison.pct_difference) == (None, None)


def test_hr_gets_the_difference_for_small_groups(db_session: Session) -> None:
    _employees(db_session, "DE", *[6_000_000] * 3)
    _employees(db_session, "FR", *[5_000_000] * 10)

    comparison = service.compare_groups(
        db_session,
        _principal(Role.HR_MANAGER),
        InsightQuery(country=["DE"]),
        InsightQuery(country=["FR"]),
        CompareMetric.MEDIAN,
    )

    assert (comparison.difference, comparison.a_suppressed) == (1_000_000, False)


# Overlapping populations: a minus b would be the pay of the few people only one side has.


def _overlap(session: Session) -> None:
    for _ in range(6):
        make_employee(session, country="DE", base_minor=6_000_000)
    make_employee(session, country="DE", base_minor=4_321_000, employment_type="PART_TIME")
    make_employee(session, country="DE", base_minor=9_876_000, level="L4")


@pytest.mark.parametrize("metric", [CompareMetric.TOTAL_COST, CompareMetric.MEAN])
@pytest.mark.parametrize(
    ("a", "b", "larger"),
    [
        (  # all employment types against full-time only: one part-timer apart
            InsightQuery(country=["DE"], employment_type=[]),
            InsightQuery(country=["DE"]),
            "a",
        ),
        (  # L3 and L4 against L3 only: one L4 apart
            InsightQuery(country=["DE"], level=[Level.L3, Level.L4]),
            InsightQuery(country=["DE"], level=[Level.L3]),
            "a",
        ),
        (  # the same, with the bigger group second
            InsightQuery(country=["DE"], level=[Level.L3]),
            InsightQuery(country=["DE"], level=[Level.L3, Level.L4]),
            "b",
        ),
    ],
    ids=["employment-type", "level", "level-reversed"],
)
def test_reproduce_viewer_cannot_isolate_a_few_people_by_overlapping_groups(
    db_session: Session, a: InsightQuery, b: InsightQuery, larger: str, metric: CompareMetric
) -> None:
    _overlap(db_session)

    comparison = service.compare_groups(db_session, _principal(Role.VIEWER), a, b, metric)

    assert (comparison.difference, comparison.pct_difference) == (None, None)
    value, suppressed = (
        (comparison.a, comparison.a_suppressed)
        if larger == "a"
        else (comparison.b, comparison.b_suppressed)
    )
    assert (value, suppressed) == (None, True)


def test_overlapping_groups_far_apart_still_compare_for_a_viewer(db_session: Session) -> None:
    _overlap(db_session)
    for _ in range(5):
        make_employee(db_session, country="DE", base_minor=5_000_000, level="L4")

    comparison = service.compare_groups(
        db_session,
        _principal(Role.VIEWER),
        InsightQuery(country=["DE"], level=[Level.L3, Level.L4]),
        InsightQuery(country=["DE"], level=[Level.L3]),
        CompareMetric.HEADCOUNT,
    )

    assert comparison.difference == 6  # six L4s apart: no one person stands out


def test_hr_gets_the_difference_of_overlapping_groups(db_session: Session) -> None:
    _overlap(db_session)

    comparison = service.compare_groups(
        db_session,
        _principal(Role.HR_MANAGER),
        InsightQuery(country=["DE"], employment_type=[]),
        InsightQuery(country=["DE"]),
        CompareMetric.TOTAL_COST,
    )

    assert comparison.difference == 4_321_000
