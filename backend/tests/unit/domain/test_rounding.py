"""Half-even rounding, checked against Python's exact Fraction rounding (also half-even)."""

from decimal import Decimal
from fractions import Fraction

import pytest
from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.rounding import divide_half_even, round_half_even, round_ratio


@pytest.mark.parametrize(
    ("value", "rounded"),
    [("0.5", 0), ("1.5", 2), ("2.5", 2), ("-0.5", 0), ("-1.5", -2), ("2.4999", 2), ("2.5001", 3)],
)
def test_round_half_even_sends_ties_to_the_even_neighbour(value: str, rounded: int) -> None:
    assert round_half_even(Decimal(value)) == rounded


@pytest.mark.parametrize(
    ("ratio", "shown"),
    [
        (Decimal("0.79999"), "0.80"),
        (Decimal("0.925"), "0.92"),
        (Decimal("0.935"), "0.94"),
        (Decimal(12) / 41, "0.29"),
        (Decimal("1"), "1.00"),
    ],
)
def test_round_ratio_shows_two_decimal_places_half_even(ratio: Decimal, shown: str) -> None:
    assert str(round_ratio(ratio)) == shown


@given(numerator=st.integers(), denominator=st.integers(min_value=1))
def test_divide_half_even_matches_exact_fraction_rounding(numerator: int, denominator: int) -> None:
    assert divide_half_even(numerator, denominator) == round(Fraction(numerator, denominator))
