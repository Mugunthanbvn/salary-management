"""The full seed: `--seed 42 --employees 10000` in memory (docs/12 sections 8 and 12, docs/14 5.6).

The 10k seed takes about 2.5 s, so it runs in the default suite. Its tests share one xdist group,
so a run seeds it once. If the generator changes on purpose, update the GOLDEN_* values and
the counts in the same commit and say why in the commit message.
"""

from collections import defaultdict
from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from salary_api.core.db import create_db_engine, create_session_factory
from salary_api.domain.enums import EmployeeStatus, PayEquityFlag
from salary_api.domain.pay_equity import compa_ratio, department_rollup, flag, pay_equity_summary
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import Country, Department, FxRate, JobRole, PayBand
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.seed.generator import Dataset, generate
from salary_api.seed.loader import load, migrate
from salary_api.seed.users import demo_users
from tests.factories import FAST_PASSWORD_HASHER, make_seed_settings, make_settings
from tests.seed_checks import active_employee_pay, employee_checksum, history_checksum

GOLDEN_10K = "b40ac43181867ca39528d16b0899337cafbd9b1608c43b72f8a2330e47801bef"
GOLDEN_HISTORY_10K = "c1637caa0425c1b40f421c1f46aada97c8f5dd9cc2870506304c2670b38d13ee"
SALARY_RECORDS, COMPONENTS, TERMINATED = 24_052, 39_562, 300

pytestmark = pytest.mark.xdist_group("seed_10k")


@pytest.fixture(scope="module")
def dataset() -> Dataset:
    """Generated when first needed, not at import, so other workers never pay for it."""
    return generate(seed=42, employees=10_000)


@pytest.fixture(scope="module")
def full_seed(dataset: Dataset) -> Iterator[Engine]:
    engine = create_db_engine(make_settings())
    try:
        migrate(engine)
        with engine.begin() as connection:
            load(connection, dataset, demo_users(make_seed_settings(), FAST_PASSWORD_HASHER))
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session(full_seed: Engine) -> Iterator[Session]:
    with create_session_factory(full_seed)() as session:
        yield session


def test_seed_42_with_10000_employees_matches_the_golden_checksums(full_seed: Engine) -> None:
    with full_seed.connect() as connection:
        assert employee_checksum(connection) == GOLDEN_10K
        assert history_checksum(connection) == GOLDEN_HISTORY_10K


def test_seed_42_gives_the_pinned_numbers_of_records_components_and_leavers(
    session: Session,
) -> None:
    counts = [
        session.scalar(select(func.count()).select_from(SalaryRecord)),
        session.scalar(select(func.count()).select_from(SalaryComponent)),
        session.scalar(select(func.count()).where(Employee.status == EmployeeStatus.TERMINATED)),
    ]

    assert counts == [SALARY_RECORDS, COMPONENTS, TERMINATED]


def test_seed_42_gives_the_documented_count_per_country(session: Session) -> None:
    by_country = select(Employee.country_code, func.count()).group_by(Employee.country_code)

    counts = {country: count for country, count in session.execute(by_country)}

    assert counts == {
        "US": 3000,
        "IN": 2500,
        "GB": 1000,
        "DE": 800,
        "CA": 600,
        "FR": 500,
        "SG": 500,
        "AU": 400,
        "JP": 400,
        "BR": 300,
    }


def test_seed_42_gives_the_documented_count_per_department(session: Session) -> None:
    by_department = (
        select(Department.name, func.count())
        .select_from(Employee)
        .join(JobRole, JobRole.id == Employee.job_role_id)
        .join(Department, Department.id == JobRole.department_id)
        .group_by(Department.name)
    )

    counts = {department: count for department, count in session.execute(by_department)}

    assert counts == {
        "Engineering": 3500,
        "Sales": 1500,
        "Operations": 1000,
        "Customer Success": 1000,
        "Marketing": 800,
        "Product": 600,
        "Finance": 600,
        "HR": 500,
        "Legal": 500,
    }


def test_every_employee_has_records_and_the_latest_is_the_current_salary(
    session: Session,
) -> None:
    latest: dict[int, tuple[object, ...]] = {}
    records = session.execute(
        select(
            SalaryRecord.employee_id,
            SalaryRecord.id,
            SalaryRecord.currency,
            SalaryRecord.base_minor,
            SalaryRecord.total_minor,
        ).order_by(SalaryRecord.employee_id, SalaryRecord.effective_date, SalaryRecord.id)
    )
    for employee_id, record_id, currency, base, total in records:
        latest[employee_id] = (record_id, currency, base, total)

    current = {
        employee_id: (record_id, currency, base, total)
        for employee_id, record_id, currency, base, total in session.execute(
            select(
                Employee.id,
                Employee.current_salary_record_id,
                Employee.currency,
                Employee.current_base_minor,
                Employee.current_total_minor,
            )
        )
    }

    assert len(current) == 10_000
    assert latest == current


def test_no_amount_is_zero_or_negative_and_yen_are_whole(session: Session) -> None:
    smallest = [
        session.scalar(select(func.min(column)))
        for column in (SalaryRecord.base_minor, SalaryComponent.amount_minor, PayBand.min_minor)
    ]
    yen = session.scalars(select(SalaryRecord.base_minor).where(SalaryRecord.currency == "JPY"))

    assert all(amount is not None and amount > 0 for amount in smallest)
    assert all(amount % 10_000 == 0 for amount in yen)


def test_every_currency_has_an_fx_rate_and_every_email_is_unique(session: Session) -> None:
    currencies = set(session.scalars(select(Country.default_currency)))
    rates = set(session.scalars(select(FxRate.currency)))
    emails = session.scalar(select(func.count(func.distinct(Employee.email))))

    assert currencies <= rates
    assert emails == 10_000


def test_every_active_employee_has_a_pay_band(session: Session) -> None:
    pays = [pay for _, pay in active_employee_pay(session)]

    assert pay_equity_summary(pays).employees_without_band == 0
    assert all(pay.band_mid is not None for pay in pays)


def test_german_customer_success_has_a_median_compa_ratio_of_about_0_92(session: Session) -> None:
    customer_success = session.scalars(
        select(Department.id).where(Department.name == "Customer Success")
    ).one()

    rollups = department_rollup(pay for _, pay in active_employee_pay(session))

    team = next(r for r in rollups if (r.department_id, r.country_code) == (customer_success, "DE"))
    assert Decimal("0.90") <= team.ratios.median_compa_ratio <= Decimal("0.94")


def test_german_customer_success_is_the_only_german_department_below_threshold(
    session: Session,
) -> None:
    names = {id_: name for id_, name in session.execute(select(Department.id, Department.name))}

    rollups = department_rollup(pay for _, pay in active_employee_pay(session))

    below = [
        names[r.department_id] for r in rollups if r.country_code == "DE" and r.below_threshold
    ]
    assert below == ["Customer Success"]


def test_planted_outliers_are_flagged_underpaid_or_overpaid(
    session: Session, dataset: Dataset
) -> None:
    flags: dict[int, PayEquityFlag] = {}
    for employee, pay in active_employee_pay(session):
        ratio = compa_ratio(pay.base, pay.band_mid, pay.employment_type).value
        if ratio is not None:
            flags[employee.id] = flag(ratio)

    planted = defaultdict(set)
    for employee_id in dataset.story.underpaid_ids:
        planted[PayEquityFlag.UNDERPAID].add(flags[employee_id])
    for employee_id in dataset.story.overpaid_ids:
        planted[PayEquityFlag.OVERPAID].add(flags[employee_id])

    assert planted == {
        PayEquityFlag.UNDERPAID: {PayEquityFlag.UNDERPAID},
        PayEquityFlag.OVERPAID: {PayEquityFlag.OVERPAID},
    }
