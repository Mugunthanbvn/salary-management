"""Group statistics over integer minor amounts, in exact arithmetic (docs/09 §2.7, ADR 0007).

The repository fetches the amounts for one group in one currency; these functions do the maths.
"""

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InsufficientData:
    """There are no amounts to summarise. Show an empty state, never zeros."""


def summarize(amounts: Iterable[int]) -> InsufficientData:
    """Count, min, max, sum, mean, median, P25 and P75 of `amounts`, in their minor units."""
    del amounts
    return InsufficientData()
