"""Pay equity: compa-ratio against the band midpoint, flags, cohorts and rollups (docs/09 §3.8)."""

from decimal import Decimal

import pytest

from salary_api.domain.enums import EmploymentType
from salary_api.domain.money import CurrencyMismatchError, Money
from salary_api.domain.pay_equity import CompaRatio, NoCompaRatioReason, compa_ratio

FULL_TIME = EmploymentType.FULL_TIME


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


def test_compa_ratio_refuses_a_band_in_another_currency() -> None:
    with pytest.raises(CurrencyMismatchError):
        compa_ratio(Money(9000000, "USD"), Money(5000000, "EUR"), FULL_TIME)
