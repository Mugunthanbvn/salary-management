"""Loading the seed into a database (docs/12-seed-data.md sections 12-13, docs/14 section 5.6).

A 200-employee seed is loaded once per module into its own in-memory database; the tests read it.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, func, select
from sqlalchemy.orm import Session

from salary_api.core.db import create_db_engine, create_session_factory
from salary_api.core.permissions import Principal, Role
from salary_api.domain.enums import EmployeeStatus, SalaryReason
from salary_api.modules.audit.models import AuditEvent
from salary_api.modules.employees.models import Employee
from salary_api.modules.reference.models import Country, Department, FxRate, JobRole, PayBand
from salary_api.modules.salaries import repository as salary_history
from salary_api.modules.salaries import service as salaries
from salary_api.modules.salaries.models import SalaryComponent, SalaryRecord
from salary_api.modules.users.models import User
from salary_api.seed.errors import SeedRefused
from salary_api.seed.generator import generate
from salary_api.seed.loader import load
from salary_api.seed.rows import UserRow
from salary_api.seed.users import demo_users
from tests.conftest import upgrade_to_head
from tests.factories import FAST_PASSWORD_HASHER, make_seed_settings, make_settings

DATASET = generate(seed=42, employees=200)


def _users() -> list[UserRow]:
    return demo_users(make_seed_settings(), FAST_PASSWORD_HASHER)


def _fresh_engine() -> Engine:
    engine = create_db_engine(make_settings())
    upgrade_to_head(engine)
    return engine


def _count(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


@pytest.fixture(scope="module")
def seeded() -> Iterator[Engine]:
    engine = _fresh_engine()
    with engine.begin() as connection:
        load(connection, DATASET, _users())
    yield engine
    engine.dispose()


@pytest.fixture
def session(seeded: Engine) -> Iterator[Session]:
    with create_session_factory(seeded)() as session:
        yield session


@pytest.mark.parametrize(
    ("model", "rows"),
    [
        (User, lambda d: 3),
        (Country, lambda d: len(d.countries)),
        (Department, lambda d: len(d.departments)),
        (JobRole, lambda d: len(d.job_roles)),
        (PayBand, lambda d: len(d.pay_bands)),
        (FxRate, lambda d: len(d.fx_rates)),
        (Employee, lambda d: len(d.employees)),
        (SalaryRecord, lambda d: len(d.salary_records)),
        (SalaryComponent, lambda d: len(d.salary_components)),
    ],
)
def test_every_table_holds_the_generated_rows(
    session: Session, model: type[Any], rows: Any
) -> None:
    assert _count(session, model) == rows(DATASET)


def test_the_latest_salary_record_is_every_employees_current_salary(session: Session) -> None:
    for employee in session.scalars(select(Employee)):
        latest = salary_history.latest_record(session, employee.id)
        assert latest is not None
        assert employee.current_salary_record_id == latest.id
        assert (employee.currency, employee.current_base_minor, employee.current_total_minor) == (
            latest.currency,
            latest.base_minor,
            latest.total_minor,
        )
        assert (employee.job_role_id, employee.level) == (latest.job_role_id, latest.level)


def test_no_employee_is_left_without_a_current_salary_record(session: Session) -> None:
    missing = select(func.count()).where(Employee.current_salary_record_id.is_(None))

    assert session.scalar(missing) == 0


def test_no_amount_is_zero_or_negative(session: Session) -> None:
    smallest = [
        session.scalar(select(func.min(column)))
        for column in (SalaryRecord.base_minor, SalaryComponent.amount_minor, PayBand.min_minor)
    ]

    assert all(amount is not None and amount > 0 for amount in smallest)


def test_japanese_amounts_are_whole_yen(session: Session) -> None:
    yen = session.scalars(select(SalaryRecord.base_minor).where(SalaryRecord.currency == "JPY"))

    amounts = list(yen)

    assert amounts
    assert all(amount % 10_000 == 0 for amount in amounts)


def test_every_country_currency_has_an_fx_rate(session: Session) -> None:
    currencies = set(session.scalars(select(Country.default_currency)))
    rates = set(session.scalars(select(FxRate.currency)))

    assert currencies <= rates


def test_every_email_is_unique_and_lowercase(session: Session) -> None:
    emails = list(session.scalars(select(Employee.email)))

    assert len(emails) == len(set(emails)) == 200
    assert all(email == email.lower() for email in emails)


def test_seeded_timestamps_come_from_dates_not_the_clock(session: Session) -> None:
    records = session.scalars(select(SalaryRecord)).all()
    employees = session.scalars(select(Employee)).all()

    assert all(
        r.created_at == datetime.combine(r.effective_date, time(tzinfo=UTC)) for r in records
    )
    assert all(e.created_at == datetime.combine(e.hire_date, time(tzinfo=UTC)) for e in employees)
    assert max(e.updated_at for e in employees) <= datetime(2026, 10, 1, tzinfo=UTC)


def test_seeded_history_has_no_acting_user(session: Session) -> None:
    assert session.scalar(select(func.count()).where(SalaryRecord.changed_by.is_not(None))) == 0


def test_the_salary_history_service_reads_a_seeded_employee(session: Session) -> None:
    hr = Principal(user_id=2, email="hr@acme.example", full_name="Hema", role=Role.HR_MANAGER)

    employee = session.get_one(Employee, 1)

    history = salaries.salary_history(session, hr, employee.id)

    assert history.records[0].reason == SalaryReason.HIRE
    assert history.records[-1].id == employee.current_salary_record_id


def test_loading_into_a_database_that_has_data_is_refused_without_reset(seeded: Engine) -> None:
    with seeded.connect() as connection, pytest.raises(SeedRefused, match="--reset"):
        load(connection, DATASET, _users())


def test_reset_replaces_everything_including_users_and_audit_events() -> None:
    engine = _fresh_engine()
    with engine.begin() as connection:
        load(connection, generate(seed=1, employees=50), _users())
    with create_session_factory(engine)() as session:
        session.add(AuditEvent(actor_id=1, action="auth.login", entity="auth"))
        session.commit()
    replacement = generate(seed=2, employees=30)

    with engine.begin() as connection:
        load(connection, replacement, _users(), reset=True)

    with create_session_factory(engine)() as session:
        codes = list(session.scalars(select(Employee.employee_code).order_by(Employee.id)))
        assert codes == [e.employee_code for e in replacement.employees]
        assert _count(session, SalaryRecord) == len(replacement.salary_records)
        assert _count(session, User) == 3
        assert _count(session, AuditEvent) == 0
    engine.dispose()


def test_rows_are_inserted_in_chunks() -> None:
    engine = _fresh_engine()
    batches: list[int] = []

    @event.listens_for(engine, "before_cursor_execute")
    def count_batches(
        _conn: Any, _cursor: Any, statement: str, parameters: Any, _context: Any, many: bool
    ) -> None:
        if many and statement.startswith("INSERT INTO salary_components"):
            batches.append(len(parameters))

    with engine.begin() as connection:
        load(connection, DATASET, _users(), chunk_size=100)

    assert sum(batches) == len(DATASET.salary_components)
    assert max(batches) == 100
    assert len(batches) == -(-len(DATASET.salary_components) // 100)
    engine.dispose()


def test_a_seeded_hr_manager_signs_in_and_finds_employees(
    client: TestClient, db_session: Session
) -> None:
    load(db_session.connection(), DATASET, _users())
    someone = DATASET.employees[0]

    login = client.post(
        "/api/v1/auth/login", json={"email": "hr@acme.example", "password": "change-me-hr"}
    )
    found = client.get("/api/v1/employees", params={"q": someone.employee_code})

    assert login.status_code == 200
    assert [item["employee_code"] for item in found.json()["items"]] == [someone.employee_code]
    assert found.json()["items"][0]["status"] == EmployeeStatus(someone.status)
