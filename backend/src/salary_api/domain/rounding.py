"""Half-even rounding to whole minor units: the one rounding mode the app uses (glossary §3).

Used for FX conversion, means, percentiles and the monthly display amount.
"""

from decimal import ROUND_HALF_EVEN, Decimal


def round_half_even(value: Decimal) -> int:
    """`value` rounded to the nearest int, ties to even (2.5 -> 2, 3.5 -> 4)."""
    return int(value.to_integral_value(rounding=ROUND_HALF_EVEN))


def divide_half_even(numerator: int, denominator: int) -> int:
    """`numerator / denominator` rounded to the nearest int, ties to even.

    Exact integer maths, so the result is right at any size. `denominator` must be positive.
    """
    quotient, remainder = divmod(numerator, denominator)
    twice_remainder = 2 * remainder
    if twice_remainder > denominator or (twice_remainder == denominator and quotient % 2 == 1):
        quotient += 1
    return quotient
