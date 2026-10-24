"""Pay equity: compa-ratio against the band midpoint, flags, cohorts and rollups (docs/09 §3.8)."""

from decimal import Decimal
from typing import Any

import pytest

from salary_api.domain.enums import EmploymentType, Level, PayEquityFlag
from salary_api.domain.money import CurrencyMismatchError, Money
from salary_api.domain.pay_equity import (
    CohortKey,
    CompaRatio,
    CompaRatioSummary,
    EmployeePay,
    NoCompaRatioReason,
    compa_ratio,
    department_rollup,
    flag,
)

FULL_TIME = EmploymentType.FULL_TIME


def make_pay(**overrides: Any) -> EmployeePay:
    """A full-time DE employee paid exactly the band midpoint, unless overridden."""
    values: dict[str, Any] = {
        "department_id": 1,
        "job_role_id": 10,
        "level": Level.L2,
        "country_code": "DE",
        "employment_type": FULL_TIME,
        "base": Money(5000000, "EUR"),
        "band_mid": Money(5000000, "EUR"),
    }
    return EmployeePay(**(values | overrides))


@pytest.mark.parametrize(
    ("base_minor", "mid_minor", "ratio"),
    [
        (4600000, 5000000, Decimal("0.92")),
        (5000000, 5000000, Decimal("1")),
        (79999, 100000, Decimal("0.79999")),  # kept unrounded: shown as 0.80, flagged on 0.79999
    ],
)
def test_compa_ratio_is_base_over_band_midpoint_unrounded(
    base_minor: int, mid_minor: int, ratio: Decimal
) -> None:
    result = compa_ratio(Money(base_minor, "EUR"), Money(mid_minor, "EUR"), FULL_TIME)

    assert result == CompaRatio(ratio)


def test_a_plain_full_time_string_from_the_database_counts_as_full_time() -> None:
    result = compa_ratio(Money(4600000, "EUR"), Money(5000000, "EUR"), "FULL_TIME")  # type: ignore[arg-type]

    assert result == CompaRatio(Decimal("0.92"))


def test_an_employee_with_no_band_has_no_compa_ratio_and_reason_no_band() -> None:
    result = compa_ratio(Money(4600000, "EUR"), None, FULL_TIME)

    assert result == CompaRatio(None, NoCompaRatioReason.NO_BAND)
    assert NoCompaRatioReason.NO_BAND == "no_band"


@pytest.mark.parametrize("employment_type", [EmploymentType.PART_TIME, EmploymentType.CONTRACTOR])
@pytest.mark.parametrize("band_mid", [Money(5000000, "EUR"), None])
def test_only_full_time_employees_get_a_compa_ratio(
    employment_type: EmploymentType, band_mid: Money | None
) -> None:
    result = compa_ratio(Money(2300000, "EUR"), band_mid, employment_type)

    assert result == CompaRatio(None, NoCompaRatioReason.NOT_FULL_TIME)


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        (Decimal("0.5"), PayEquityFlag.UNDERPAID),
        (Decimal("0.79999"), PayEquityFlag.UNDERPAID),  # rounds to 0.80 for display only
        (Decimal("0.80"), PayEquityFlag.IN_BAND),
        (Decimal("1"), PayEquityFlag.IN_BAND),
        (Decimal("1.20"), PayEquityFlag.IN_BAND),
        (Decimal("1.20001"), PayEquityFlag.OVERPAID),  # rounds to 1.20 for display only
        (Decimal("1.5"), PayEquityFlag.OVERPAID),
    ],
)
def test_flag_compares_the_unrounded_ratio_with_inclusive_band_edges(
    ratio: Decimal, expected: PayEquityFlag
) -> None:
    assert flag(ratio) is expected


def test_a_ratio_summary_has_count_median_mean_and_flag_counts() -> None:
    ratios = [Decimal(r) for r in ("0.70", "0.78", "0.80", "1.00", "1.20", "1.52")]

    summary = CompaRatioSummary.of(ratios)

    assert summary == CompaRatioSummary(
        count=6,
        median_compa_ratio=Decimal("0.90"),
        mean_compa_ratio=Decimal("1.00"),
        underpaid_count=2,  # 0.80 and 1.20 are in band
        overpaid_count=1,
    )


def test_pct_below_band_is_the_unrounded_share_of_underpaid_people() -> None:
    ratios = [Decimal("0.70")] * 12 + [Decimal("1.00")] * 29

    summary = CompaRatioSummary.of(ratios)

    assert summary.pct_below_band == Decimal(12) / 41  # shown as 0.29


def test_a_ratio_summary_needs_at_least_one_ratio() -> None:
    with pytest.raises(ValueError, match="no values"):
        CompaRatioSummary.of([])


def test_compa_ratio_refuses_a_band_in_another_currency() -> None:
    with pytest.raises(CurrencyMismatchError):
        compa_ratio(Money(9000000, "USD"), Money(5000000, "EUR"), FULL_TIME)


def test_a_cohort_is_the_job_role_level_and_country() -> None:
    pay = make_pay(job_role_id=7, level=Level.L3, country_code="IN")

    assert pay.cohort == CohortKey(job_role_id=7, level=Level.L3, country_code="IN")


def test_people_in_different_departments_share_a_cohort() -> None:
    support, engineering = make_pay(department_id=1), make_pay(department_id=2)

    assert support.cohort == engineering.cohort


def paid_at(ratio: str, **overrides: Any) -> EmployeePay:
    """An employee whose base is `ratio` x a EUR 1,000,000.00 band midpoint."""
    base = Money.from_major(Decimal(ratio) * 1000000, "EUR")
    return make_pay(base=base, band_mid=Money(100000000, "EUR"), **overrides)


def test_rollup_is_the_median_compa_ratio_per_department_and_country() -> None:
    engineering = [paid_at(r, department_id=1) for r in ("0.95", "1.05", "1.00")]
    customer_success = [paid_at(r, department_id=3) for r in ("0.90", "0.94", "0.92")]

    rollup = department_rollup(customer_success + engineering)

    assert [(row.department_id, row.country_code, row.count) for row in rollup] == [
        (1, "DE", 3),
        (3, "DE", 3),
    ]
    assert [row.median_compa_ratio for row in rollup] == [Decimal("1.00"), Decimal("0.92")]


def test_rollup_keeps_countries_of_one_department_apart() -> None:
    france = paid_at("1.10", country_code="FR")
    germany = paid_at("0.90", country_code="DE")

    rollup = department_rollup([france, germany])

    assert [(row.country_code, row.median_compa_ratio) for row in rollup] == [
        ("DE", Decimal("0.90")),
        ("FR", Decimal("1.10")),
    ]


def test_rollup_leaves_out_employees_without_a_compa_ratio() -> None:
    evaluated = paid_at("1.00")
    part_time = paid_at("0.50", employment_type=EmploymentType.PART_TIME)
    no_band = make_pay(base=Money(2500000, "EUR"), band_mid=None)
    contractor_only = paid_at("0.40", department_id=9, employment_type=EmploymentType.CONTRACTOR)

    rollup = department_rollup([evaluated, part_time, no_band, contractor_only])

    assert [(row.department_id, row.count, row.median_compa_ratio) for row in rollup] == [
        (1, 1, Decimal("1.00"))
    ]


@pytest.mark.parametrize(
    ("ratios", "below_threshold"),
    [
        (("0.90", "0.92", "0.94"), True),  # the seeded DE Customer Success gap
        (("0.9499",), True),
        (("0.95",), False),  # exactly 0.95 is not below
        (("0.90", "1.00"), False),  # median 0.95
        (("0.95", "1.00", "1.05"), False),
    ],
)
def test_a_department_is_below_threshold_when_its_median_is_under_0_95(
    ratios: tuple[str, ...], below_threshold: bool
) -> None:
    (row,) = department_rollup([paid_at(ratio) for ratio in ratios])

    assert row.below_threshold is below_threshold
