"""The generated dataset, before any database (docs/12-seed-data.md sections 2-7, 9-12)."""

import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from functools import cache

import time_machine

from salary_api.domain.enums import EmployeeStatus, EmploymentType, SalaryReason
from salary_api.domain.search import employee_search_text
from salary_api.seed import seed_config as config
from salary_api.seed.allocation import largest_remainder
from salary_api.seed.generator import Dataset, generate

EMAIL = re.compile(r"[a-z0-9]+\.[a-z0-9]+\.[0-9]{4}@acme\.example")
COUNTRY_CODES = [country.code for country in config.COUNTRIES]


@cache
def _dataset(seed: int = 42, employees: int = 200, *, history: bool = True) -> Dataset:
    return generate(seed=seed, employees=employees, history=history)


def _department_of_role(dataset: Dataset) -> dict[int, str]:
    names = {department.id: department.name for department in dataset.departments}
    return {role.id: names[role.department_id] for role in dataset.job_roles}


def test_employee_counts_per_country_are_exact_for_any_total() -> None:
    dataset = _dataset(employees=200)

    counts = Counter(employee.country_code for employee in dataset.employees)

    assert [counts[code] for code in COUNTRY_CODES] == [60, 50, 20, 16, 12, 10, 10, 8, 8, 6]


def test_department_counts_are_exact_within_each_country() -> None:
    dataset = _dataset(employees=1000)
    department_of = _department_of_role(dataset)
    shares = [department.share for department in config.DEPARTMENTS]

    for country in config.COUNTRIES:
        people = [e for e in dataset.employees if e.country_code == country.code]
        counts = Counter(department_of[e.job_role_id] for e in people)

        expected = largest_remainder(len(people), shares)
        assert [counts[d.name] for d in config.DEPARTMENTS] == expected


def test_employment_types_are_split_exactly_within_each_country() -> None:
    dataset = _dataset(employees=1000)
    shares = [share for _, share in config.EMPLOYMENT_TYPES]

    for country in config.COUNTRIES:
        people = [e for e in dataset.employees if e.country_code == country.code]
        counts = Counter(e.employment_type for e in people)

        expected = largest_remainder(len(people), shares)
        assert [counts[kind] for kind, _ in config.EMPLOYMENT_TYPES] == expected


def test_every_level_is_one_the_job_role_allows() -> None:
    dataset = _dataset()
    roles = {role.title: role for d in config.DEPARTMENTS for role in d.roles}
    allowed = {row.id: roles[row.title].levels for row in dataset.job_roles}

    assert all(e.level in allowed[e.job_role_id] for e in dataset.employees)
    assert all(r.level in allowed[r.job_role_id] for r in dataset.salary_records)


def test_employee_codes_are_sequential_in_hire_date_order() -> None:
    employees = _dataset().employees

    assert [e.employee_code for e in employees] == [f"ACME-{n:06d}" for n in range(1, 201)]
    assert [e.id for e in employees] == list(range(1, 201))
    assert [e.hire_date for e in employees] == sorted(e.hire_date for e in employees)


def test_emails_are_unique_ascii_and_end_with_the_last_four_digits_of_the_code() -> None:
    employees = _dataset(employees=1000).employees

    assert len({e.email for e in employees}) == 1000
    assert all(EMAIL.fullmatch(e.email) for e in employees)
    assert all(e.email.split("@")[0].endswith(e.employee_code[-4:]) for e in employees)


def test_search_text_is_the_folded_name_code_and_email() -> None:
    employees = _dataset().employees

    assert all(
        e.search_text == employee_search_text(e.first_name, e.last_name, e.employee_code, e.email)
        for e in employees
    )


def test_every_salary_is_in_the_country_currency() -> None:
    dataset = _dataset()
    currency_of = {country.code: country.default_currency for country in dataset.countries}
    employee_currency = {e.id: e.currency for e in dataset.employees}

    assert all(e.currency == currency_of[e.country_code] for e in dataset.employees)
    assert all(r.currency == employee_currency[r.employee_id] for r in dataset.salary_records)


def test_japanese_salaries_are_whole_yen_rounded_to_ten_thousand() -> None:
    dataset = _dataset()

    yen = [r.base_minor for r in dataset.salary_records if r.currency == "JPY"]

    assert yen
    assert all(amount % 10_000 == 0 for amount in yen)


def test_hire_dates_fall_within_eleven_years_before_the_anchor_date() -> None:
    employees = _dataset(employees=1000).employees

    assert all(date(2015, 10, 1) <= e.hire_date < date(2026, 10, 1) for e in employees)


def test_about_three_percent_are_terminated_after_their_hire_date() -> None:
    employees = _dataset(employees=1000).employees

    terminated = [e for e in employees if e.status == EmployeeStatus.TERMINATED]

    assert len(terminated) == 30
    for employee in terminated:
        assert employee.termination_date is not None
        assert employee.hire_date < employee.termination_date <= date(2026, 10, 1)
    assert all(e.termination_date is None for e in employees if e not in terminated)


def test_no_salary_record_is_dated_after_the_termination_date() -> None:
    dataset = _dataset(employees=1000)
    ended = {e.id: e.termination_date for e in dataset.employees if e.termination_date}

    assert all(
        record.effective_date <= ended[record.employee_id]
        for record in dataset.salary_records
        if record.employee_id in ended
    )


def test_every_employee_has_a_hire_record_and_the_latest_record_is_the_current_salary() -> None:
    dataset = _dataset()
    records = defaultdict(list)
    for record in dataset.salary_records:
        records[record.employee_id].append(record)

    for employee in dataset.employees:
        history = records[employee.id]
        latest = history[-1]
        assert history[0].reason == SalaryReason.HIRE
        assert history[0].effective_date == employee.hire_date
        assert employee.current_salary_record_id == latest.id
        assert (employee.current_base_minor, employee.current_total_minor) == (
            latest.base_minor,
            latest.total_minor,
        )
        assert (employee.job_role_id, employee.level) == (latest.job_role_id, latest.level)


def test_a_record_total_is_its_base_plus_its_components() -> None:
    dataset = _dataset()
    components = defaultdict(int)
    for component in dataset.salary_components:
        components[component.salary_record_id] += component.amount_minor

    assert all(r.total_minor == r.base_minor + components[r.id] for r in dataset.salary_records)
    assert all(r.base_minor > 0 for r in dataset.salary_records)
    assert all(c.amount_minor > 0 for c in dataset.salary_components)


def test_contractors_have_no_components() -> None:
    dataset = _dataset(employees=1000)
    contractor_ids = {
        e.id for e in dataset.employees if e.employment_type == EmploymentType.CONTRACTOR
    }
    contractor_records = {r.id for r in dataset.salary_records if r.employee_id in contractor_ids}

    assert contractor_records
    assert not any(c.salary_record_id in contractor_records for c in dataset.salary_components)


def test_seeded_history_has_no_acting_user_and_ids_count_up() -> None:
    dataset = _dataset()

    assert all(r.changed_by is None for r in dataset.salary_records)
    assert [r.id for r in dataset.salary_records] == list(range(1, len(dataset.salary_records) + 1))
    assert [c.id for c in dataset.salary_components] == list(
        range(1, len(dataset.salary_components) + 1)
    )


def test_history_averages_about_three_records_per_employee() -> None:
    dataset = _dataset(employees=1000)

    per_employee = Counter(r.employee_id for r in dataset.salary_records)

    assert 2.3 < len(dataset.salary_records) / 1000 < 3.5
    assert min(per_employee.values()) >= 1


def test_without_history_each_employee_has_one_hire_record_at_the_same_current_salary() -> None:
    with_history, without = _dataset(), _dataset(history=False)

    assert len(without.salary_records) == 200
    assert all(r.reason == SalaryReason.HIRE for r in without.salary_records)
    assert [(e.employee_code, e.current_base_minor) for e in without.employees] == [
        (e.employee_code, e.current_base_minor) for e in with_history.employees
    ]


def test_reference_data_has_ten_countries_nine_departments_and_35_roles() -> None:
    dataset = _dataset()

    assert [c.code for c in dataset.countries] == COUNTRY_CODES
    assert [d.name for d in dataset.departments] == [d.name for d in config.DEPARTMENTS]
    assert len(dataset.job_roles) == 35


def test_there_is_one_pay_band_per_role_level_and_country() -> None:
    dataset = _dataset()

    keys = {(b.job_role_id, b.level, b.country_code) for b in dataset.pay_bands}

    assert len(dataset.pay_bands) == len(keys) == 1360
    assert all(b.effective_from == date(2026, 1, 1) for b in dataset.pay_bands)
    assert all((e.job_role_id, e.level, e.country_code) in keys for e in dataset.employees)


def test_the_fx_snapshot_has_a_rate_for_every_country_currency() -> None:
    dataset = _dataset()

    rates = {rate.currency: rate for rate in dataset.fx_rates}

    assert {c.default_currency for c in dataset.countries} == set(rates)
    assert all(rate.as_of == date(2026, 10, 1) for rate in rates.values())
    assert {rate.source for rate in rates.values()} == {"illustrative static snapshot"}


def test_the_same_seed_gives_the_same_dataset() -> None:
    assert generate(seed=42, employees=200) == generate(seed=42, employees=200)


def test_another_seed_gives_another_dataset() -> None:
    first, second = _dataset(seed=42), _dataset(seed=43)

    assert [e.current_base_minor for e in first.employees] != [
        e.current_base_minor for e in second.employees
    ]


def test_the_dataset_does_not_depend_on_the_wall_clock() -> None:
    with time_machine.travel(datetime(2026, 10, 1, tzinfo=UTC), tick=False):
        today = generate(seed=7, employees=50)
    with time_machine.travel(datetime(2027, 3, 15, tzinfo=UTC), tick=False):
        next_year = generate(seed=7, employees=50)

    assert today == next_year
