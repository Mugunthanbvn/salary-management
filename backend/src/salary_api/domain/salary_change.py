"""Rules for salary changes: what a promotion is, and how much the base changed."""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

from salary_api.domain.enums import Level
from salary_api.domain.money import Money

_LEVEL_ORDER: Final = list(Level)  # L1 (lowest) .. L6 (highest)
_HUNDREDTH: Final = Decimal("0.01")


def is_promotion(*, old_level: Level, new_level: Level, old_role_id: int, new_role_id: int) -> bool:
    """A PROMOTION moves to a higher level or to a different job role."""
    return new_role_id != old_role_id or _LEVEL_ORDER.index(new_level) > _LEVEL_ORDER.index(
        old_level
    )


def base_change_pct(previous: Money, current: Money) -> Decimal | None:
    """The change from `previous` to `current` base in percent, two decimals, half-even.

    None when the currency changed (a relocation): the two amounts are not comparable.
    """
    if previous.currency != current.currency:
        return None
    change = Decimal(current.amount_minor - previous.amount_minor) * 100 / previous.amount_minor
    return change.quantize(_HUNDREDTH, rounding=ROUND_HALF_EVEN)
