"""FX conversion to USD at read time with dated Decimal rates (ADR 0005, docs/09 §2.6)."""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.currency import UnknownCurrencyError
from salary_api.domain.money import FxRate, InvalidFxRateError, Money, to_usd

AS_OF = date(2026, 10, 1)
RATES = {
    "USD": FxRate("USD", Decimal("1"), AS_OF),
    "EUR": FxRate("EUR", Decimal("1.085"), AS_OF),
    "JPY": FxRate("JPY", Decimal("0.0067"), AS_OF),
    "INR": FxRate("INR", Decimal("0.01198"), AS_OF),
}


def test_fx_rate_holds_a_decimal_rate_and_its_date() -> None:
    rate = FxRate("EUR", Decimal("1.085"), AS_OF)

    assert (rate.currency, rate.rate_to_usd, rate.as_of) == ("EUR", Decimal("1.085"), AS_OF)


@pytest.mark.parametrize("rate_to_usd", [1.085, 1, "1.085"])
def test_fx_rate_rejects_a_float_rate(rate_to_usd: object) -> None:
    with pytest.raises(TypeError, match="Decimal"):
        FxRate("EUR", rate_to_usd, AS_OF)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("currency", "rate_to_usd"),
    [
        ("EUR", Decimal("0")),
        ("EUR", Decimal("-1.085")),
        ("EUR", Decimal("NaN")),
        ("EUR", Decimal("Infinity")),
        ("USD", Decimal("1.1")),
    ],
)
def test_fx_rate_rejects_a_rate_that_cannot_be_right(currency: str, rate_to_usd: Decimal) -> None:
    with pytest.raises(InvalidFxRateError, match=currency):
        FxRate(currency, rate_to_usd, AS_OF)


def test_fx_rate_rejects_an_unsupported_currency() -> None:
    with pytest.raises(UnknownCurrencyError):
        FxRate("XYZ", Decimal("1"), AS_OF)


@pytest.mark.parametrize(
    ("money", "usd_minor"),
    [
        (Money(5200000, "EUR"), 5642000),  # €52,000.00 x 1.085 = $56,420.00
        (Money(6500000, "JPY"), 4355000),  # ¥6,500,000 x 0.0067 = $43,550.00
        (Money(120000000, "INR"), 1437600),  # ₹12,00,000.00 x 0.01198 = $14,376.00
    ],
)
def test_to_usd_converts_with_the_decimal_rate_and_currency_exponent(
    money: Money, usd_minor: int
) -> None:
    result = to_usd(money, RATES)

    assert result.amount == Money(usd_minor, "USD")


def test_to_usd_tags_the_result_with_the_rate_as_of_date() -> None:
    rates = {"GBP": FxRate("GBP", Decimal("1.27"), date(2026, 9, 30))}

    result = to_usd(Money(100, "GBP"), rates)

    assert result.fx_as_of == date(2026, 9, 30)


@pytest.mark.parametrize(("amount_minor", "usd_minor"), [(1, 0), (3, 2), (5, 2), (7, 4)])
def test_to_usd_rounds_half_even_to_the_cent(amount_minor: int, usd_minor: int) -> None:
    rates = {"GBP": FxRate("GBP", Decimal("0.5"), AS_OF)}

    result = to_usd(Money(amount_minor, "GBP"), rates)

    assert result.amount == Money(usd_minor, "USD")


@given(amount_minor=st.integers(min_value=-(10**18), max_value=10**18))
def test_usd_to_usd_is_the_identity(amount_minor: int) -> None:
    money = Money(amount_minor, "USD")

    result = to_usd(money, RATES)

    assert result.amount == money


def test_to_usd_leaves_the_source_amount_unchanged() -> None:
    money = Money(5200000, "EUR")

    to_usd(money, RATES)

    assert money == Money(5200000, "EUR")
