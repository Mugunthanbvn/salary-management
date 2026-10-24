"""Comparing amounts in different currencies by USD value (docs/07-api-spec.md 6.1).

A USD salary range becomes exact local bounds per currency, and a USD salary sort becomes an
integer key that SQL can order by. Both agree with `to_usd`, the one conversion function.
"""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.currency import USD
from salary_api.domain.money import (
    USD_SORT_SCALE,
    FxRate,
    Money,
    UsdSortKey,
    max_local_amount,
    min_local_amount,
    to_usd,
    usd_sort_key,
)

AS_OF = date(2026, 10, 1)
INT64_MAX = 2**63 - 1


def _rate(currency: str, rate_to_usd: str) -> FxRate:
    return FxRate(currency, Decimal(rate_to_usd), AS_OF)


def _usd(amount_minor: int, rate: FxRate) -> int:
    return to_usd(Money(amount_minor, rate.currency), {rate.currency: rate}).amount.amount_minor


@st.composite
def rates(draw: st.DrawFn) -> FxRate:
    """A non-USD rate with up to 6 decimal places, from 0.000001 to 10 USD per unit."""
    currency = draw(st.sampled_from(["EUR", "GBP", "INR", "JPY", "BRL", "SGD"]))
    rate = draw(st.decimals(min_value=Decimal("0.000001"), max_value=Decimal(10), places=6))
    return FxRate(currency, rate, AS_OF)


usd_bounds = st.integers(min_value=0, max_value=10**12)


@pytest.mark.parametrize("usd_minor", [0, 1, 5_000_000])
def test_usd_bounds_are_the_same_amount_in_usd(usd_minor: int) -> None:
    usd = _rate(USD, "1")

    assert (min_local_amount(usd_minor, usd), max_local_amount(usd_minor, usd)) == (
        usd_minor,
        usd_minor,
    )


def test_usd_bounds_cover_every_amount_that_converts_to_the_bound() -> None:
    yen = _rate("JPY", "0.0067")  # ¥1 = 0.67 US cents

    assert (min_local_amount(670, yen), max_local_amount(670, yen)) == (1000, 1000)
    assert (min_local_amount(671, yen), max_local_amount(671, yen)) == (1001, 1002)


@pytest.mark.parametrize(("usd_minor", "smallest"), [(1, 2), (2, 3)])
def test_usd_bounds_follow_half_even_rounding(usd_minor: int, smallest: int) -> None:
    half = _rate("GBP", "0.5")  # 1 penny = 0.5 cents: 1 -> 0, 2 -> 1, 3 -> 2 (half-even)

    assert min_local_amount(usd_minor, half) == smallest


@given(rate=rates(), usd_minor=usd_bounds)
def test_min_local_amount_is_the_smallest_amount_worth_at_least_the_bound(
    rate: FxRate, usd_minor: int
) -> None:
    smallest = min_local_amount(usd_minor, rate)

    assert _usd(smallest, rate) >= usd_minor
    assert smallest == 0 or _usd(smallest - 1, rate) < usd_minor


@given(rate=rates(), usd_minor=usd_bounds)
def test_max_local_amount_is_the_largest_amount_worth_at_most_the_bound(
    rate: FxRate, usd_minor: int
) -> None:
    largest = max_local_amount(usd_minor, rate)

    assert _usd(largest, rate) <= usd_minor
    assert _usd(largest + 1, rate) > usd_minor


@pytest.mark.parametrize(
    ("currency", "rate_to_usd", "factor"),
    [
        ("USD", "1", 1_000_000),
        ("EUR", "1.085", 1_085_000),
        ("JPY", "0.0067", 670_000),  # yen have no minor unit: 1 yen = 0.67 cents
        ("INR", "0.01198", 11_980),
    ],
)
def test_usd_sort_key_is_us_cents_per_local_minor_unit_scaled_to_an_integer(
    currency: str, rate_to_usd: str, factor: int
) -> None:
    key = usd_sort_key(_rate(currency, rate_to_usd))

    assert key == UsdSortKey(factor=factor, cap=INT64_MAX // factor)
    assert (
        factor
        == Decimal(rate_to_usd) * 10 ** (2 - (0 if currency == "JPY" else 2)) * USD_SORT_SCALE
    )


@given(
    rate_a=rates(),
    rate_b=rates(),
    amount_a=st.integers(min_value=0, max_value=10**12),
    amount_b=st.integers(min_value=0, max_value=10**12),
)
def test_a_smaller_usd_sort_key_never_means_more_usd(
    rate_a: FxRate, rate_b: FxRate, amount_a: int, amount_b: int
) -> None:
    key_a, key_b = usd_sort_key(rate_a), usd_sort_key(rate_b)
    sort_a = min(amount_a, key_a.cap) * key_a.factor
    sort_b = min(amount_b, key_b.cap) * key_b.factor

    if sort_a < sort_b:
        assert _usd(amount_a, rate_a) <= _usd(amount_b, rate_b)
    assert max(sort_a, sort_b) <= INT64_MAX
