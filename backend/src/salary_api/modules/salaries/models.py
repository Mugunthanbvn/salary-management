"""Salary history (docs/06-data-model.md sections 4.6 and 4.7). Rows are never changed."""

from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from salary_api.core.append_only import append_only
from salary_api.core.models import Base, UtcDateTime, utc_now
from salary_api.domain.enums import ComponentType, Level, SalaryReason
from salary_api.modules.reference.models import JobRole, level_column
from salary_api.modules.users.models import User


@append_only
class SalaryComponent(Base):
    """An annual allowance or bonus target, in its record's currency (ADR 0010)."""

    __tablename__ = "salary_components"
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="amount_not_negative"),
        UniqueConstraint(
            "salary_record_id", "type", "name", name="uq_salary_components_record_type_name"
        ),
        Index("ix_salary_components_record", "salary_record_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    salary_record_id: Mapped[int] = mapped_column(ForeignKey("salary_records.id"))
    type: Mapped[ComponentType] = mapped_column(
        Enum(
            ComponentType,
            name="component_type",
            native_enum=False,
            create_constraint=True,
            length=20,
        )
    )
    name: Mapped[str] = mapped_column(String(60))
    amount_minor: Mapped[int] = mapped_column(BigInteger)


@append_only
class SalaryRecord(Base):
    """One salary event. The current salary is the greatest (effective_date, id) (ADR 0006)."""

    __tablename__ = "salary_records"
    __table_args__ = (
        CheckConstraint("base_minor > 0", name="base_positive"),
        CheckConstraint("total_minor >= base_minor", name="total_at_least_base"),
        Index("ix_salary_records_employee_effective", "employee_id", "effective_date", "id"),
        Index("ix_salary_records_effective_reason", "effective_date", "reason"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    effective_date: Mapped[date]
    currency: Mapped[str] = mapped_column(CHAR(3))  # the country's currency at that time
    base_minor: Mapped[int] = mapped_column(BigInteger)  # annual
    total_minor: Mapped[int] = mapped_column(BigInteger)  # base + every component
    # Snapshots of the role and level at that moment, so history explains promotions.
    job_role_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"))
    level: Mapped[Level] = mapped_column(level_column())
    reason: Mapped[SalaryReason] = mapped_column(
        Enum(SalaryReason, name="reason", native_enum=False, create_constraint=True, length=20)
    )
    note: Mapped[str | None] = mapped_column(String(500))
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # null when seeded
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)

    components: Mapped[list[SalaryComponent]] = relationship(order_by=SalaryComponent.id)
    job_role: Mapped[JobRole] = relationship()
    changed_by_user: Mapped[User | None] = relationship()
