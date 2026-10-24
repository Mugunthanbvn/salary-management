"""The employees table (docs/06-data-model.md section 4.5)."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import CHAR, BigInteger, CheckConstraint, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from salary_api.core.models import Base, UtcDateTime, utc_now
from salary_api.domain.enums import EmployeeStatus, EmploymentType, Level
from salary_api.modules.reference.models import JobRole, level_column

if TYPE_CHECKING:
    from salary_api.modules.salaries.models import SalaryRecord


class Employee(Base):
    """An employee. The current salary is copied from the latest salary record (section 6.2).

    `version` is the optimistic lock: every UPDATE also says `WHERE version = <the version
    read>`, and the service sets the next version itself (ADR 0013).
    """

    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "(status = 'TERMINATED') = (termination_date IS NOT NULL)",
            name="terminated_has_date",
        ),
        CheckConstraint("termination_date >= hire_date", name="terminated_after_hire"),
        CheckConstraint("current_base_minor > 0", name="current_base_positive"),
        CheckConstraint(
            "current_total_minor >= current_base_minor", name="current_total_at_least_base"
        ),
        # docs/19-performance.md section 5: the query each index serves.
        Index("ix_employees_country_status", "country_code", "status"),
        Index("ix_employees_job_role_level", "job_role_id", "level"),
        Index("ix_employees_status_employment_type", "status", "employment_type"),
        Index("ix_employees_currency_base", "currency", "current_base_minor"),
        Index("ix_employees_last_first", "last_name", "first_name"),
        Index("ix_employees_search_text", "search_text"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(12), unique=True)  # ACME-######
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    # fold(first last code email), maintained by the service (domain/search.py).
    search_text: Mapped[str] = mapped_column(String(600))
    job_role_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"))
    level: Mapped[Level] = mapped_column(level_column())
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(
            EmploymentType,
            name="employment_type",
            native_enum=False,
            create_constraint=True,
            length=12,
        )
    )
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, name="status", native_enum=False, create_constraint=True, length=10),
        default=EmployeeStatus.ACTIVE,
    )
    hire_date: Mapped[date]
    termination_date: Mapped[date | None]
    # The current salary: always the country's currency (docs/06 section 4.2).
    currency: Mapped[str] = mapped_column(CHAR(3))
    current_base_minor: Mapped[int] = mapped_column(BigInteger)
    current_total_minor: Mapped[int] = mapped_column(BigInteger)
    # Null only inside the transaction that creates the employee and its HIRE record.
    current_salary_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("salary_records.id", use_alter=True)
    )
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)

    job_role: Mapped[JobRole] = relationship()
    current_salary_record: Mapped["SalaryRecord | None"] = relationship(
        foreign_keys=[current_salary_record_id]
    )

    __mapper_args__: ClassVar[dict[str, Any]] = {
        "version_id_col": version,
        "version_id_generator": False,
    }

    @validates("email")
    def _normalise_email(self, _key: str, email: str) -> str:
        """Trimmed and lowercased, so the unique index is case-insensitive."""
        return email.strip().lower()
