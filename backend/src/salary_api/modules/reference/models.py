"""Reference tables (docs/06-data-model.md sections 4.2-4.4, 4.8 and 4.8a).

All are seeded. Pay bands and FX rates have no write endpoint in v1.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from salary_api.core.models import Base, UtcDateTime, utc_now
from salary_api.domain.currency import SUPPORTED_CURRENCIES
from salary_api.domain.enums import Level


class JobFamily(StrEnum):
    """The pay family of a job role; the seed's band multipliers use it (docs/12 section 3)."""

    ENGINEERING = "ENGINEERING"
    PRODUCT = "PRODUCT"
    DESIGN = "DESIGN"
    SALES = "SALES"
    CUSTOMER_SUCCESS = "CUSTOMER_SUCCESS"
    MARKETING = "MARKETING"
    OPERATIONS = "OPERATIONS"
    FINANCE = "FINANCE"
    PEOPLE = "PEOPLE"
    LEGAL = "LEGAL"


def level_column() -> Enum:
    """`L1`..`L6` stored as VARCHAR(2) with a CHECK (docs/06-data-model.md section 3)."""
    return Enum(Level, name="level", native_enum=False, create_constraint=True, length=2)


class Country(Base):
    """A country ACME employs people in. Every salary there is in `default_currency`."""

    __tablename__ = "countries"
    __table_args__ = (
        CheckConstraint(
            column("default_currency").in_(sorted(SUPPORTED_CURRENCIES)),
            name="default_currency_supported",
        ),
    )

    code: Mapped[str] = mapped_column(CHAR(2), primary_key=True)  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(80))
    default_currency: Mapped[str] = mapped_column(CHAR(3))  # ISO 4217
    # Inactive countries are hidden from forms and import.
    is_active: Mapped[bool] = mapped_column(default=True)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class JobRole(Base):
    """A job title from the controlled list, so pay-equity cohorts cannot fragment."""

    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(80), unique=True)
    # A role belongs to exactly one department; employees reach it through their role.
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    family: Mapped[JobFamily] = mapped_column(
        Enum(JobFamily, name="family", native_enum=False, create_constraint=True, length=30)
    )

    department: Mapped[Department] = relationship()


class PayBand(Base):
    """The pay-equity benchmark for a job role + level + country, in that country's currency."""

    __tablename__ = "pay_bands"
    __table_args__ = (
        CheckConstraint("min_minor > 0", name="min_positive"),
        CheckConstraint("mid_minor >= min_minor", name="mid_at_least_min"),
        CheckConstraint("max_minor >= mid_minor", name="max_at_least_mid"),
        # The current band is the latest effective_from on or before today.
        UniqueConstraint("job_role_id", "level", "country_code", "effective_from"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_role_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"))
    level: Mapped[Level] = mapped_column(level_column())
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    currency: Mapped[str] = mapped_column(CHAR(3))  # the country's default currency
    min_minor: Mapped[int] = mapped_column(BigInteger)
    mid_minor: Mapped[int] = mapped_column(BigInteger)
    max_minor: Mapped[int] = mapped_column(BigInteger)
    effective_from: Mapped[date]


class FxRate(Base):
    """The current USD rate of one currency. Converted amounts are never stored (ADR 0005)."""

    __tablename__ = "fx_rates"

    currency: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    # USD per one major unit, as a decimal string so SQLite loses no precision.
    rate_to_usd: Mapped[str] = mapped_column(String(32))
    as_of: Mapped[date]
    source: Mapped[str] = mapped_column(String(80))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
