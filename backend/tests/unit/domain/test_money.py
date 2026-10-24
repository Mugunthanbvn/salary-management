"""Money: integer minor units plus an ISO 4217 code (ADR 0004, docs/06-data-model.md §5)."""

import dataclasses
import operator
from collections.abc import Callable
from decimal import Decimal

import pytest
from hypothesis import given

from salary_api.domain.currency import UnknownCurrencyError
from salary_api.domain.money import (
    AmountTooLargeError,
    CurrencyMismatchError,
    InvalidAmountError,
    Money,
    TooManyDecimalsError,
)
from tests.unit.domain.strategies import amounts_minor, currencies, major_amounts


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
    "major",
    [
        "1_000",  # Python digit grouping, a thousands separator in disguise
        "١٢٣.٤٥",  # Arabic-Indic digits for 123.45
        "１２３",  # noqa: RUF001 (full-width digits for 123, ambiguous on purpose)
        "1e3",
        "1E+30",
        " 12.50",
        "12.50\n",
        "12.",
        ".5",
    ],
)
def test_from_major_accepts_only_plain_ascii_decimal_text(major: str) -> None:
    with pytest.raises(InvalidAmountError, match="not a number"):
        Money.from_major(major, "USD")


@pytest.mark.parametrize(("major", "amount_minor"), [("+12.50", 1250), ("-12.5", -1250)])
def test_from_major_accepts_a_leading_sign(major: str, amount_minor: int) -> None:
    assert Money.from_major(major, "USD") == Money(amount_minor, "USD")


@pytest.mark.parametrize(
    ("major", "currency"),
    [
        ("10000000000000.00", "USD"),  # 10**15 cents: one past the cap
        ("1000000000000000", "JPY"),
        ("-10000000000000", "EUR"),
        ("1" + "0" * 30, "USD"),
        (Decimal("1E+30"), "USD"),  # used to become 10**32 and overflow BIGINT at insert
        (Decimal("1E+10000000"), "INR"),  # used to build a 33-million-bit int
    ],
)
def test_from_major_rejects_amounts_of_10_to_the_15_minor_units_or_more(
    major: str | Decimal, currency: str
) -> None:
    with pytest.raises(InvalidAmountError, match="too large"):
        Money.from_major(major, currency)


@pytest.mark.parametrize(
    ("major", "currency", "amount_minor"),
    [
        ("9999999999999.99", "USD", 999999999999999),
        ("999999999999999", "JPY", 999999999999999),
        ("-9999999999999.99", "EUR", -999999999999999),
        pytest.param("1." + "0" * 100000, "USD", 100, id="100000-trailing-zeros"),
    ],
)
def test_from_major_accepts_amounts_up_to_the_cap(
    major: str, currency: str, amount_minor: int
) -> None:
    money = Money.from_major(major, currency)

    assert money == Money(amount_minor, currency)


@pytest.mark.parametrize(
    ("major", "error"),
    [
        (Decimal("1E+999999999"), InvalidAmountError),
        (Decimal("1E-999999999"), TooManyDecimalsError),
    ],
)
def test_from_major_rejects_extreme_exponents_at_once(
    major: Decimal, error: type[Exception]
) -> None:
    with pytest.raises(error):
        Money.from_major(major, "USD")


def test_from_major_reads_zero_with_any_exponent_as_zero() -> None:
    assert Money.from_major(Decimal("0E+999999999"), "USD") == Money(0, "USD")


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


def test_money_in_the_same_currency_adds_and_subtracts_exactly() -> None:
    a, b = Money(100, "EUR"), Money(250, "EUR")

    assert (a + b, a - b) == (Money(350, "EUR"), Money(-150, "EUR"))


@pytest.mark.parametrize("operation", [operator.add, operator.sub])
def test_adding_or_subtracting_different_currencies_raises(
    operation: Callable[[Money, Money], Money],
) -> None:
    with pytest.raises(CurrencyMismatchError, match=r"EUR.*INR"):
        operation(Money(100, "EUR"), Money(100, "INR"))


@pytest.mark.parametrize(
    ("annual", "monthly"),
    [
        (Money(6000000, "EUR"), Money(500000, "EUR")),
        (Money(100, "USD"), Money(8, "USD")),
        (Money(11, "USD"), Money(1, "USD")),
        (Money(1000000, "JPY"), Money(83333, "JPY")),
        (Money(6, "GBP"), Money(0, "GBP")),
        (Money(18, "GBP"), Money(2, "GBP")),
        (Money(30, "GBP"), Money(2, "GBP")),
        (Money(42, "GBP"), Money(4, "GBP")),
    ],
)
def test_monthly_display_is_annual_over_12_rounded_half_even(annual: Money, monthly: Money) -> None:
    result = annual.monthly_display()

    assert result == monthly


@given(amount_minor=amounts_minor, currency=currencies)
def test_from_major_of_to_major_round_trips_every_amount(amount_minor: int, currency: str) -> None:
    money = Money(amount_minor, currency)

    assert Money.from_major(money.to_major(), currency) == money


@given(major_amounts())
def test_to_major_of_from_major_round_trips_every_valid_major_amount(
    amount_and_currency: tuple[Decimal, str],
) -> None:
    major, currency = amount_and_currency

    assert Money.from_major(major, currency).to_major() == major


def test_an_amount_over_the_cap_is_its_own_kind_of_invalid_amount() -> None:
    with pytest.raises(AmountTooLargeError) as raised:
        Money.from_major("10000000000000", "EUR")

    assert isinstance(raised.value, InvalidAmountError)
