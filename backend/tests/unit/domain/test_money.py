"""Money: integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5)."""

import dataclasses
from decimal import Decimal

import pytest

from salary_api.domain.money import Money


def test_money_holds_integer_minor_units_and_a_currency() -> None:
    money = Money(123456, "USD")

    assert (money.amount_minor, money.currency) == (123456, "USD")


def test_money_is_immutable() -> None:
    money = Money(100, "EUR")

    with pytest.raises(dataclasses.FrozenInstanceError):
        money.amount_minor = 200  # type: ignore[misc]


@pytest.mark.parametrize("amount", [1234.56, 100.0, True, Decimal("100"), "100"])
def test_money_rejects_float_amounts(amount: object) -> None:
    with pytest.raises(TypeError, match="int"):
        Money(amount, "USD")  # type: ignore[arg-type]
