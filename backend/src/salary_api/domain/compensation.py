"""Total compensation: annual base plus allowances plus bonus targets (ADR 0010).

Equity, commission, overtime and benefits are out of scope, so there is nothing else to add.
"""

from collections.abc import Iterable

from salary_api.domain.money import Money


def total_compensation(base: Money, components: Iterable[Money]) -> Money:
    """Base + the amount of every ALLOWANCE and BONUS_TARGET component, all annual.

    Every component must be in the base's currency (CurrencyMismatchError otherwise).
    """
    total = base
    for component in components:
        total += component
    return total
