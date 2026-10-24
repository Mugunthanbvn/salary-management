"""Total compensation = base + allowances + bonus targets (ADR 0010, docs/09 §2.2)."""

import pytest

from salary_api.domain.compensation import total_compensation
from salary_api.domain.money import CurrencyMismatchError, Money


def test_total_is_base_plus_allowances_plus_bonus_target() -> None:
    base = Money.from_major("1200000", "INR")
    hra = Money.from_major("480000", "INR")
    transport = Money.from_major("24000", "INR")
    target_bonus = Money.from_major("120000", "INR")

    total = total_compensation(base, [hra, transport, target_bonus])

    assert total == Money.from_major("1824000", "INR")  # ADR 0010's worked example


def test_total_without_components_is_the_base() -> None:
    base = Money(5200000, "EUR")

    assert total_compensation(base, []) == base


def test_a_component_in_another_currency_from_the_base_is_rejected() -> None:
    base = Money(5200000, "EUR")
    meal_allowance = Money(120000, "EUR")
    usd_bonus = Money(500000, "USD")

    with pytest.raises(CurrencyMismatchError, match="USD"):
        total_compensation(base, [meal_allowance, usd_bonus])
