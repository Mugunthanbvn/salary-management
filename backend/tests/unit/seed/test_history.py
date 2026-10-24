"""Salary history walked back from the current salary (docs/12-seed-data.md section 7)."""

import random
from collections import Counter
from datetime import date, timedelta
from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st

from salary_api.domain.enums import Level, SalaryReason
from salary_api.seed.history import HistoryEntry, back_cast, hire_only

END = date(2026, 10, 1)
UNIT = 100_000  # 1,000.00 in cents
ALL_LEVELS = tuple(Level)


def _history(
    seed: int,
    *,
    hire_date: date = date(2016, 3, 15),
    end_date: date = END,
    base: int = 10_000_000,
    level: Level = Level.L3,
    levels: tuple[Level, ...] = ALL_LEVELS,
) -> list[HistoryEntry]:
    return back_cast(
        random.Random(seed),
        hire_date=hire_date,
        end_date=end_date,
        current_base_minor=base,
        current_level=level,
        allowed_levels=levels,
        unit_minor=UNIT,
    )


@given(
    seed=st.integers(min_value=0, max_value=10_000),
    tenure_days=st.integers(min_value=1, max_value=4018),
    base_units=st.integers(min_value=20, max_value=500),
    level=st.sampled_from(ALL_LEVELS),
)
def test_history_starts_with_the_hire_and_ends_at_the_current_salary(
    seed: int, tenure_days: int, base_units: int, level: Level
) -> None:
    hire_date = END - timedelta(days=tenure_days)

    entries = _history(seed, hire_date=hire_date, base=base_units * UNIT, level=level)

    assert entries[0].reason == SalaryReason.HIRE
    assert entries[0].effective_date == hire_date
    assert (entries[-1].base_minor, entries[-1].level) == (base_units * UNIT, level)
    assert [e.effective_date for e in entries] == sorted(e.effective_date for e in entries)
    assert all(hire_date <= e.effective_date <= END for e in entries)
    assert all(e.base_minor > 0 and e.base_minor % UNIT == 0 for e in entries)
    assert [e.reason for e in entries].count(SalaryReason.HIRE) == 1


def test_raises_and_promotions_never_lower_pay() -> None:
    for seed in range(300):
        entries = _history(seed)
        for before, after in pairwise(entries):
            if after.reason in (
                SalaryReason.MERIT,
                SalaryReason.PROMOTION,
                SalaryReason.MARKET_ADJUSTMENT,
            ):
                assert after.base_minor >= before.base_minor


def test_merit_raises_are_two_to_six_percent_on_about_55_percent_of_anniversaries() -> None:
    raises = [
        (before.base_minor, after.base_minor)
        for seed in range(400)
        for before, after in pairwise(_history(seed))
        if after.reason == SalaryReason.MERIT
    ]

    anniversaries = 400 * 10  # 2016-03-15 to 2026-10-01
    assert 0.48 < len(raises) / anniversaries < 0.58
    assert all(1.015 <= after / before <= 1.065 for before, after in raises)


def test_about_15_percent_of_employees_get_one_promotion_up_one_level() -> None:
    histories = [_history(seed) for seed in range(1000)]

    promoted = [h for h in histories if any(e.reason == SalaryReason.PROMOTION for e in h)]

    assert 0.12 < len(promoted) / len(histories) < 0.18
    for entries in promoted:
        assert Counter(e.reason for e in entries)[SalaryReason.PROMOTION] == 1
        assert entries[0].level == Level.L2
        promotion = next(e for e in entries if e.reason == SalaryReason.PROMOTION)
        assert promotion.level == Level.L3


def test_no_promotion_back_to_a_level_the_role_does_not_allow() -> None:
    allowed = (Level.L4, Level.L5, Level.L6)

    histories = [_history(seed, level=Level.L4, levels=allowed) for seed in range(300)]

    assert all(e.level == Level.L4 for entries in histories for e in entries)


def test_a_terminated_employee_has_no_record_after_the_termination_date() -> None:
    termination = date(2021, 1, 10)

    histories = [_history(seed, end_date=termination) for seed in range(200)]

    assert all(e.effective_date <= termination for h in histories for e in h)


def test_market_adjustments_and_corrections_are_rare() -> None:
    reasons = Counter(e.reason for seed in range(4000) for e in _history(seed))

    assert 0 < reasons[SalaryReason.MARKET_ADJUSTMENT] < 4000 * 0.02
    assert 0 < reasons[SalaryReason.CORRECTION] < 4000 * 0.01


def test_a_recent_hire_usually_has_only_the_hire_record() -> None:
    histories = [_history(seed, hire_date=date(2026, 2, 1)) for seed in range(200)]

    assert sum(len(h) == 1 for h in histories) > 190


def test_without_history_there_is_one_hire_record_at_the_current_salary() -> None:
    entries = hire_only(hire_date=date(2020, 5, 4), current_base_minor=7_000_000, level=Level.L2)

    assert entries == [HistoryEntry(date(2020, 5, 4), SalaryReason.HIRE, Level.L2, 7_000_000)]


def test_a_leap_day_hire_has_its_anniversary_on_28_february() -> None:
    dates = {
        e.effective_date
        for seed in range(100)
        for e in _history(seed, hire_date=date(2020, 2, 29))
        if e.reason == SalaryReason.MERIT
    }

    assert date(2021, 2, 28) in dates
    assert date(2024, 2, 29) in dates
