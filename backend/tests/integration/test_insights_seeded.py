"""Pay equity on the full seed (`--seed 42 --employees 10000`, story on): the planted findings
show up through the insights service (docs/12-seed-data.md section 8, docs/18 B6).

The seed takes a few seconds, so the module seeds once and shares the seed's xdist group.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
import time_machine
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from salary_api.core.db import create_db_engine, create_session_factory
from salary_api.core.permissions import Principal, Role
from salary_api.modules.insights import service
from salary_api.modules.insights.schemas import (
    PayEquityCohorts,
    PayEquityDepartments,
    PayEquityQuery,
    PayEquityView,
)
from salary_api.modules.reference.models import Country
from salary_api.seed.generator import generate
from salary_api.seed.loader import load, migrate
from salary_api.seed.users import demo_users
from tests.factories import FAST_PASSWORD_HASHER, make_seed_settings, make_settings

pytestmark = pytest.mark.xdist_group("seed_10k")

HR = Principal(user_id=1, email="hr@acme.example", full_name="HR", role=Role.HR_MANAGER)


@pytest.fixture(scope="module")
def session() -> Iterator[Session]:
    engine: Engine = create_db_engine(make_settings())
    try:
        migrate(engine)
        with engine.begin() as connection:
            load(
                connection,
                generate(seed=42, employees=10_000),
                demo_users(make_seed_settings(), FAST_PASSWORD_HASHER),
            )
        with (
            time_machine.travel(datetime(2026, 10, 1, 9, tzinfo=UTC), tick=False),
            create_session_factory(engine)() as session,
        ):
            yield session
    finally:
        engine.dispose()


def _departments(session: Session, country: str) -> PayEquityDepartments:
    query = PayEquityQuery(view=PayEquityView.DEPARTMENTS, country=[country])
    result = service.pay_equity(session, HR, query)
    assert isinstance(result, PayEquityDepartments)
    return result


def test_customer_success_in_germany_is_paid_systematically_below_band(session: Session) -> None:
    groups = {group.department.name: group for group in _departments(session, "DE").groups}

    customer_success = groups["Customer Success"]
    assert customer_success.median_compa_ratio == "0.93"  # about 0.929
    assert customer_success.below_threshold is True


def test_it_is_the_only_department_below_threshold_in_any_country(session: Session) -> None:
    below = [
        (country, group.department.name)
        for country in session.scalars(select(Country.code).order_by(Country.code))
        for group in _departments(session, country).groups
        if group.below_threshold
    ]

    assert below == [("DE", "Customer Success")]


def test_the_flagged_employees_are_exactly_the_planted_outliers(session: Session) -> None:
    result = service.pay_equity(session, HR, PayEquityQuery())

    assert isinstance(result, PayEquityCohorts)
    summary = result.summary
    assert (summary.employees_flagged_underpaid, summary.employees_flagged_overpaid) == (104, 70)
    assert summary.employees_without_band == 0
