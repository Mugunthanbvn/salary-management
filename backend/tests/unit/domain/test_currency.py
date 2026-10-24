"""ISO 4217 minor-unit exponents for the currencies ACME pays in (docs/12-seed-data.md §2)."""

import pytest

from salary_api.domain.currency import SUPPORTED_CURRENCIES, minor_unit_exponent

SEEDED_CURRENCY_EXPONENTS = {
    "USD": 2,
    "INR": 2,
    "GBP": 2,
    "EUR": 2,
    "CAD": 2,
    "SGD": 2,
    "AUD": 2,
    "JPY": 0,
    "BRL": 2,
}


@pytest.mark.parametrize(("currency", "exponent"), SEEDED_CURRENCY_EXPONENTS.items())
def test_each_seeded_currency_has_its_iso_4217_exponent(currency: str, exponent: int) -> None:
    result = minor_unit_exponent(currency)

    assert result == exponent


def test_supported_currencies_are_exactly_the_seeded_ones() -> None:
    assert SEEDED_CURRENCY_EXPONENTS.keys() == SUPPORTED_CURRENCIES
