"""Salary history, walked back from the current salary (docs/12-seed-data.md section 7).

The current salary is generated first and stays on its band; earlier records divide it by each
raise, so the history always ends exactly at the current salary. The random draws depend only
on dates and levels, never on amounts, so the demo story changes amounts but not events.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from salary_api.domain.enums import Level, SalaryReason
from salary_api.seed import seed_config as config
from salary_api.seed.pay import Bounds, draw_uniform, round_to_unit

_LEVELS_IN_ORDER = tuple(Level)


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One salary record: what it was, when, at which level."""

    effective_date: date
    reason: SalaryReason
    level: Level
    base_minor: int


@dataclass(frozen=True, slots=True)
class _Event:
    effective_date: date
    reason: SalaryReason
    factor: Decimal  # the base after the event divided by the base before it
    promotes: bool = False


def hire_only(*, hire_date: date, current_base_minor: int, level: Level) -> list[HistoryEntry]:
    """One HIRE record at the current salary (`--no-history`)."""
    return [HistoryEntry(hire_date, SalaryReason.HIRE, level, current_base_minor)]


def back_cast(  # noqa: PLR0913  (one keyword per fact about the employee)
    rng: random.Random,
    *,
    hire_date: date,
    end_date: date,
    current_base_minor: int,
    current_level: Level,
    allowed_levels: tuple[Level, ...],
    unit_minor: int,
) -> list[HistoryEntry]:
    """The employee's salary records, oldest first: HIRE at `hire_date`, the current salary last.

    `end_date` is the anchor date, or the termination date of a terminated employee.
    Each earlier base is the later one divided by the raise, rounded to `unit_minor` again, and
    at least one unit away from it, so every record changes the base.
    """
    events = _events(rng, hire_date, end_date, current_level, allowed_levels)
    newest_first: list[HistoryEntry] = []
    base, level = current_base_minor, current_level
    for event in reversed(events):
        newest_first.append(HistoryEntry(event.effective_date, event.reason, level, base))
        base = _earlier_base(base, event.factor, unit_minor)
        if event.promotes:
            level = _level_below(level)
    newest_first.append(HistoryEntry(hire_date, SalaryReason.HIRE, level, base))
    return newest_first[::-1]


def _events(
    rng: random.Random,
    hire_date: date,
    end_date: date,
    level: Level,
    allowed_levels: tuple[Level, ...],
) -> list[_Event]:
    """The salary events after the hire, in date order (same-day events keep this order)."""
    anniversaries = _anniversaries(hire_date, end_date)
    promotion_at = None
    if anniversaries and rng.random() < config.PROMOTION_PROBABILITY:
        promotion_at = rng.randrange(len(anniversaries))
        if level == allowed_levels[0]:  # the level below is outside the role's range
            promotion_at = None
    events: list[_Event] = []
    for index, anniversary in enumerate(anniversaries):
        if index == promotion_at:
            raise_ = _raise(rng, config.PROMOTION_RAISE)
            events.append(_Event(anniversary, SalaryReason.PROMOTION, raise_, promotes=True))
        elif rng.random() < config.MERIT_PROBABILITY:
            events.append(_Event(anniversary, SalaryReason.MERIT, _raise(rng, config.MERIT_RAISE)))
    for reason, probability, bounds in (
        (
            SalaryReason.MARKET_ADJUSTMENT,
            config.MARKET_ADJUSTMENT_PROBABILITY,
            config.MARKET_ADJUSTMENT_RAISE,
        ),
        (SalaryReason.CORRECTION, config.CORRECTION_PROBABILITY, config.CORRECTION_CHANGE),
    ):
        days = (end_date - hire_date).days
        if days >= 1 and rng.random() < probability:
            when = hire_date + timedelta(days=rng.randint(1, days))
            events.append(_Event(when, reason, _raise(rng, bounds)))
    return sorted(events, key=lambda event: event.effective_date)  # stable: same-day order kept


def _anniversaries(hire_date: date, end_date: date) -> list[date]:
    """Work anniversaries after the hire, up to `end_date`. A 29 February hire uses 28 February."""
    anniversaries: list[date] = []
    years = 1
    while (anniversary := _same_day_years_later(hire_date, years)) <= end_date:
        anniversaries.append(anniversary)
        years += 1
    return anniversaries


def _same_day_years_later(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 February in a year that has none
        return day.replace(year=day.year + years, day=28)


def _earlier_base(later_minor: int, factor: Decimal, unit_minor: int) -> int:
    """The base before an event with this factor: `later / factor`, rounded to the unit.

    Rounding can undo a small change (a 2 % raise on 19 units rounds back to 19), so the result
    is moved at least one unit the other way: a raise always raises, a cut always cuts. It never
    goes below one unit.
    """
    earlier = round_to_unit(Decimal(later_minor) / factor, unit_minor)
    if factor > 1:
        return max(min(earlier, later_minor - unit_minor), unit_minor)
    return max(earlier, later_minor + unit_minor)


def _raise(rng: random.Random, bounds: Bounds) -> Decimal:
    """1 + a change drawn from `bounds`, never exactly 1 (a CORRECTION may be either way)."""
    factor = 1 + draw_uniform(rng, bounds)
    while factor == 1:
        factor = 1 + draw_uniform(rng, bounds)
    return factor


def _level_below(level: Level) -> Level:
    return _LEVELS_IN_ORDER[_LEVELS_IN_ORDER.index(level) - 1]
