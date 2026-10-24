"""Named thresholds hold the glossary §3 numbers, as int and exact Decimal (never float)."""

from decimal import Decimal

from salary_api.domain.constants import (
    MIN_GROUP_SIZE,
    PAY_EQUITY_HIGH,
    PAY_EQUITY_LOW,
    ROLLUP_THRESHOLD,
)


def test_small_group_threshold_is_five_people() -> None:
    assert MIN_GROUP_SIZE == 5


def test_pay_equity_thresholds_are_exact_decimals_from_the_glossary() -> None:
    thresholds = (PAY_EQUITY_LOW, PAY_EQUITY_HIGH, ROLLUP_THRESHOLD)

    assert thresholds == (Decimal("0.80"), Decimal("1.20"), Decimal("0.95"))
    assert all(type(threshold) is Decimal for threshold in thresholds)
