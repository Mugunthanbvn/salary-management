"""Pay equity: compa-ratio against the band midpoint, flags, cohorts and rollups (docs/09 §3.8)."""

from decimal import Decimal
from typing import Any

import pytest

from salary_api.domain.enums import EmploymentType, Level, PayEquityFlag
from salary_api.domain.money import CurrencyMismatchError, Money
from salary_api.domain.pay_equity import (
    CohortKey,
    CompaRatio,
    EmployeePay,
    NoCompaRatioReason,
    compa_ratio,
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


def test_compa_ratio_refuses_a_band_in_another_currency() -> None:
    with pytest.raises(CurrencyMismatchError):
        compa_ratio(Money(9000000, "USD"), Money(5000000, "EUR"), FULL_TIME)


def test_a_cohort_is_the_job_role_level_and_country() -> None:
    pay = make_pay(job_role_id=7, level=Level.L3, country_code="IN")

    assert pay.cohort == CohortKey(job_role_id=7, level=Level.L3, country_code="IN")


def test_people_in_different_departments_share_a_cohort() -> None:
    support, engineering = make_pay(department_id=1), make_pay(department_id=2)

    assert support.cohort == engineering.cohort
