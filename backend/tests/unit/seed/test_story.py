"""The planted demo story and `--no-story` (docs/12-seed-data.md section 8).

The story only changes amounts: the same seed with and without it gives the same people and the
same salary events, so each planted change can be checked against the clean version.
"""

from collections import defaultdict
from decimal import Decimal
from functools import cache

from salary_api.domain.enums import EmployeeStatus, EmploymentType, PayEquityFlag
from salary_api.domain.money import Money
from salary_api.domain.pay_equity import compa_ratio, flag
from salary_api.domain.rounding import round_half_even
from salary_api.seed.generator import Dataset, generate
from salary_api.seed.rows import EmployeeRow
from tests.seed_checks import dataset_flags

EMPLOYEES = 1000


@cache
def _dataset(*, story: bool) -> Dataset:
    return generate(seed=42, employees=EMPLOYEES, story=story)


def _band_mid(dataset: Dataset, employee: EmployeeRow) -> Money:
    mids = {(b.job_role_id, b.level, b.country_code): b.mid_minor for b in dataset.pay_bands}
    mid = mids[employee.job_role_id, employee.level, employee.country_code]
    return Money(mid, employee.currency)


def _flag(dataset: Dataset, employee: EmployeeRow) -> PayEquityFlag:
    base = Money(employee.current_base_minor, employee.currency)
    ratio = compa_ratio(base, _band_mid(dataset, employee), employee.employment_type).value
    assert ratio is not None
    return flag(ratio)


def _is_de_customer_success(dataset: Dataset, employee: EmployeeRow) -> bool:
    departments = {d.id: d.name for d in dataset.departments}
    department_of = {role.id: departments[role.department_id] for role in dataset.job_roles}
    return (
        employee.country_code == "DE" and department_of[employee.job_role_id] == "Customer Success"
    )


def test_two_percent_of_active_full_timers_are_outliers_60_percent_of_them_underpaid() -> None:
    dataset = _dataset(story=True)
    eligible = [
        e
        for e in dataset.employees
        if e.employment_type == EmploymentType.FULL_TIME and e.status == EmployeeStatus.ACTIVE
    ]

    outliers = len(dataset.story.underpaid_ids) + len(dataset.story.overpaid_ids)

    assert outliers == round_half_even(Decimal(len(eligible)) * Decimal("0.02"))
    assert len(dataset.story.underpaid_ids) == round_half_even(outliers * Decimal("0.6"))
    eligible_ids = {e.id for e in eligible}
    assert set(dataset.story.underpaid_ids) | set(dataset.story.overpaid_ids) <= eligible_ids


def test_underpaid_outliers_are_flagged_underpaid_and_overpaid_ones_overpaid() -> None:
    dataset = _dataset(story=True)
    by_id = {e.id: e for e in dataset.employees}

    assert {_flag(dataset, by_id[i]) for i in dataset.story.underpaid_ids} == {
        PayEquityFlag.UNDERPAID
    }
    assert {_flag(dataset, by_id[i]) for i in dataset.story.overpaid_ids} == {
        PayEquityFlag.OVERPAID
    }


def test_outliers_sit_at_0_65_to_0_75_or_1_30_to_1_45_of_their_band_mid() -> None:
    dataset = _dataset(story=True)
    by_id = {e.id: e for e in dataset.employees}

    for ids, low, high in (
        (dataset.story.underpaid_ids, Decimal("0.64"), Decimal("0.76")),
        (dataset.story.overpaid_ids, Decimal("1.29"), Decimal("1.46")),
    ):
        for employee_id in ids:
            employee = by_id[employee_id]
            mid = _band_mid(dataset, employee).amount_minor
            assert low <= Decimal(employee.current_base_minor) / mid <= high


def test_every_german_customer_success_employee_earns_92_percent_of_the_clean_base() -> None:
    planted, clean = _dataset(story=True), _dataset(story=False)
    clean_base = {e.id: e.current_base_minor for e in clean.employees}
    outliers = set(planted.story.underpaid_ids) | set(planted.story.overpaid_ids)

    team = [e for e in planted.employees if _is_de_customer_success(planted, e)]

    assert team
    assert set(planted.story.pay_gap_ids) == {e.id for e in team}
    for employee in team:
        if employee.id not in outliers:
            expected = Decimal(clean_base[employee.id]) * Decimal("0.92")
            assert abs(employee.current_base_minor - expected) <= 50_000  # half of EUR 1,000


def test_the_story_changes_nobody_else() -> None:
    planted, clean = _dataset(story=True), _dataset(story=False)
    changed = (
        set(planted.story.underpaid_ids)
        | set(planted.story.overpaid_ids)
        | set(planted.story.pay_gap_ids)
    )

    assert [e for e in planted.employees if e.id not in changed] == [
        e for e in clean.employees if e.id not in changed
    ]


def test_the_story_scales_whole_histories_without_changing_their_events() -> None:
    planted, clean = _dataset(story=True), _dataset(story=False)

    def events(dataset: Dataset) -> dict[int, list[tuple[object, ...]]]:
        history = defaultdict(list)
        for r in dataset.salary_records:
            history[r.employee_id].append((r.effective_date, r.reason, r.level))
        return history

    assert events(planted) == events(clean)


def test_without_the_story_nobody_is_flagged_and_no_department_is_below_threshold() -> None:
    flags, below = dataset_flags(_dataset(story=False))

    assert (flags, below) == ({}, [])


def test_with_the_story_the_flagged_employees_are_exactly_the_planted_outliers() -> None:
    dataset = _dataset(story=True)

    flags, _ = dataset_flags(dataset)

    assert {i for i, f in flags.items() if f == PayEquityFlag.UNDERPAID} == set(
        dataset.story.underpaid_ids
    )
    assert {i for i, f in flags.items() if f == PayEquityFlag.OVERPAID} == set(
        dataset.story.overpaid_ids
    )


def test_without_the_story_nothing_is_planted() -> None:
    story = _dataset(story=False).story

    assert (story.underpaid_ids, story.overpaid_ids, story.pay_gap_ids) == ((), (), ())
