"""Money: integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5)."""

import dataclasses
from decimal import Decimal

import pytest

from salary_api.domain.currency import UnknownCurrencyError
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


def test_money_rejects_an_unsupported_currency() -> None:
    with pytest.raises(UnknownCurrencyError):
        Money(100, "XYZ")


@pytest.mark.parametrize(
    ("major", "currency", "amount_minor"),
    [
        ("1234.56", "USD", 123456),
        ("1234", "JPY", 1234),
        (Decimal("52000.00"), "EUR", 5200000),
        ("1200000", "INR", 120000000),
        ("0.01", "USD", 1),
        ("0", "GBP", 0),
    ],
)
def test_from_major_converts_major_units_to_minor_units(
    major: str | Decimal, currency: str, amount_minor: int
) -> None:
    money = Money.from_major(major, currency)

    assert money == Money(amount_minor, currency)
