"""Reference tables (docs/06-data-model.md sections 4.2-4.4, 4.8, 4.8a) and their constraints."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from salary_api.modules.reference.models import (
    Country,
    Department,
    FxRate,
    JobFamily,
    JobRole,
    PayBand,
)
from tests.conftest import FROZEN_NOW


def _department(session: Session, name: str = "Engineering") -> Department:
    department = Department(name=name)
    session.add(department)
    session.flush()
    return department


def _job_role(session: Session, title: str = "Software Engineer") -> JobRole:
    role = JobRole(title=title, department_id=_department(session).id, family=JobFamily.ENGINEERING)
    session.add(role)
    session.flush()
    return role


def _country(session: Session, code: str = "DE", currency: str = "EUR") -> Country:
    country = Country(code=code, name="Germany", default_currency=currency)
    session.add(country)
    session.flush()
    return country


def test_a_country_is_active_by_default(db_session: Session) -> None:
    country = _country(db_session)

    assert (country.code, country.default_currency, country.is_active) == ("DE", "EUR", True)


def test_the_database_rejects_a_country_currency_that_is_not_supported(
    db_session: Session,
) -> None:
    row = {"code": "CH", "name": "Switzerland", "default_currency": "CHF", "is_active": True}

    with pytest.raises(IntegrityError, match="CHECK"):
        db_session.execute(insert(Country).values(**row))


def test_two_departments_cannot_share_a_name(db_session: Session) -> None:
    _department(db_session, "Sales")

    with pytest.raises(IntegrityError, match="UNIQUE"):
        _department(db_session, "Sales")


def test_a_job_role_belongs_to_an_existing_department(db_session: Session) -> None:
    db_session.add(JobRole(title="Recruiter", department_id=999, family=JobFamily.PEOPLE))

    with pytest.raises(IntegrityError, match="FOREIGN KEY"):
        db_session.flush()


def test_two_job_roles_cannot_share_a_title(db_session: Session) -> None:
    role = _job_role(db_session)
    db_session.add(
        JobRole(title=role.title, department_id=role.department_id, family=JobFamily.ENGINEERING)
    )

    with pytest.raises(IntegrityError, match="UNIQUE"):
        db_session.flush()


def test_the_database_rejects_a_job_family_outside_the_seed_list(db_session: Session) -> None:
    department = _department(db_session)
    row = {"title": "Wizard", "department_id": department.id, "family": "MAGIC"}

    with pytest.raises(IntegrityError, match="CHECK"):
        db_session.execute(insert(JobRole).values(**row))


def test_job_families_are_the_seed_data_families() -> None:
    assert [family.value for family in JobFamily] == [
        "ENGINEERING",
        "PRODUCT",
        "DESIGN",
        "SALES",
        "CUSTOMER_SUCCESS",
        "MARKETING",
        "OPERATIONS",
        "FINANCE",
        "PEOPLE",
        "LEGAL",
    ]


def _band_row(session: Session, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "job_role_id": _job_role(session).id,
        "level": "L3",
        "country_code": _country(session).code,
        "currency": "EUR",
        "min_minor": 4_800_000,
        "mid_minor": 6_000_000,
        "max_minor": 7_200_000,
        "effective_from": date(2026, 1, 1),
    }
    return row | overrides


def test_a_pay_band_is_stored_with_its_minor_amounts(db_session: Session) -> None:
    db_session.execute(insert(PayBand).values(**_band_row(db_session)))

    band = db_session.query(PayBand).one()
    assert (band.level, band.currency, band.min_minor, band.mid_minor, band.max_minor) == (
        "L3",
        "EUR",
        4_800_000,
        6_000_000,
        7_200_000,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"min_minor": 0}, id="min not positive"),
        pytest.param({"mid_minor": 4_000_000}, id="mid below min"),
        pytest.param({"max_minor": 5_000_000}, id="max below mid"),
        pytest.param({"level": "L9"}, id="level outside the glossary"),
    ],
)
def test_the_database_rejects_a_pay_band_that_cannot_be_right(
    db_session: Session, overrides: dict[str, Any]
) -> None:
    with pytest.raises(IntegrityError, match="CHECK"):
        db_session.execute(insert(PayBand).values(**_band_row(db_session, **overrides)))


def test_one_band_per_role_level_country_and_start_date(db_session: Session) -> None:
    row = _band_row(db_session)
    db_session.execute(insert(PayBand).values(**row))

    with pytest.raises(IntegrityError, match="UNIQUE"):
        db_session.execute(insert(PayBand).values(**row))


def test_an_fx_rate_keeps_its_rate_as_a_decimal_string(db_session: Session) -> None:
    db_session.add(
        FxRate(
            currency="INR",
            rate_to_usd="0.01198",
            as_of=date(2026, 10, 1),
            source="Static snapshot (illustrative)",
            updated_at=FROZEN_NOW,
        )
    )
    db_session.flush()
    db_session.expunge_all()

    rate = db_session.get(FxRate, "INR")

    assert rate is not None
    assert (rate.rate_to_usd, rate.as_of, rate.updated_by) == ("0.01198", date(2026, 10, 1), None)
