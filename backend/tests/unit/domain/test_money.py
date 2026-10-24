"""Money: integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5)."""

import dataclasses
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.currency import UnknownCurrencyError
from salary_api.domain.money import InvalidAmountError, Money, TooManyDecimalsError
from tests.unit.domain.strategies import currencies, major_amounts


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


@pytest.mark.parametrize(
    ("major", "currency"),
    [("1234.5", "JPY"), ("1000.05", "JPY"), ("1.234", "USD"), ("0.001", "EUR")],
)
def test_from_major_rejects_more_decimals_than_the_currency_has(major: str, currency: str) -> None:
    with pytest.raises(TooManyDecimalsError, match=currency):
        Money.from_major(major, currency)


@pytest.mark.parametrize(
    ("major", "currency", "amount_minor"),
    [("4500000.0", "JPY", 4500000), ("52000.000", "EUR", 5200000)],
)
def test_from_major_accepts_trailing_zeros_because_nothing_is_lost(
    major: str, currency: str, amount_minor: int
) -> None:
    money = Money.from_major(major, currency)

    assert money == Money(amount_minor, currency)


@pytest.mark.parametrize("major", [1234.5, 100.0, True, 100])
def test_from_major_rejects_floats_and_other_non_text_numbers(major: object) -> None:
    with pytest.raises(TypeError, match="str or Decimal"):
        Money.from_major(major, "USD")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "major", ["abc", "", "1,234.56", "12 000", "NaN", "Infinity", "-inf", Decimal("NaN")]
)
def test_from_major_rejects_text_that_is_not_a_finite_number(major: str | Decimal) -> None:
    with pytest.raises(InvalidAmountError, match="not a number"):
        Money.from_major(major, "USD")


@pytest.mark.parametrize(
    ("money", "major"),
    [
        (Money(123456, "USD"), "1234.56"),
        (Money(1234, "JPY"), "1234"),
        (Money(5, "EUR"), "0.05"),
        (Money(-1250, "GBP"), "-12.50"),
        (Money(120000000, "INR"), "1200000.00"),
    ],
)
def test_to_major_returns_the_exact_decimal_in_major_units(money: Money, major: str) -> None:
    result = money.to_major()

    assert isinstance(result, Decimal)
    assert str(result) == major


@given(amount_minor=st.integers(), currency=currencies)
def test_from_major_of_to_major_round_trips_every_amount(amount_minor: int, currency: str) -> None:
    money = Money(amount_minor, currency)

    assert Money.from_major(money.to_major(), currency) == money


@given(major_amounts())
def test_to_major_of_from_major_round_trips_every_valid_major_amount(
    amount_and_currency: tuple[Decimal, str],
) -> None:
    major, currency = amount_and_currency

    assert Money.from_major(major, currency).to_major() == major
