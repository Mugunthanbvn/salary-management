"""Pay equity: compa-ratio against the band midpoint, flags, cohorts and rollups (docs/09 §3.8)."""

from decimal import Decimal

import pytest

from salary_api.domain.enums import EmploymentType
from salary_api.domain.money import Money
from salary_api.domain.pay_equity import CompaRatio, compa_ratio

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
