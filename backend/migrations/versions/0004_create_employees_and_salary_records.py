"""create employees and salary records

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-24 03:38:49.516854
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CURRENT_SALARY_RECORD_FK = "fk_employees_current_salary_record_id_salary_records"


def _supports_alter_constraint() -> bool:
    """SQLite cannot ALTER TABLE ... ADD CONSTRAINT (it has the key inline instead)."""
    return op.get_context().dialect.name != "sqlite"


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_code", sa.String(length=12), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("search_text", sa.String(length=600), nullable=False),
        sa.Column("job_role_id", sa.Integer(), nullable=False),
        sa.Column(
            "level",
            sa.Enum(
                "L1",
                "L2",
                "L3",
                "L4",
                "L5",
                "L6",
                name="level",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "employment_type",
            sa.Enum(
                "FULL_TIME",
                "PART_TIME",
                "CONTRACTOR",
                name="employment_type",
                native_enum=False,
                create_constraint=True,
                length=12,
            ),
            nullable=False,
        ),
        sa.Column("country_code", sa.CHAR(length=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE", "TERMINATED", name="status", native_enum=False, create_constraint=True
            ),
            nullable=False,
        ),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("current_base_minor", sa.BigInteger(), nullable=False),
        sa.Column("current_total_minor", sa.BigInteger(), nullable=False),
        sa.Column("current_salary_record_id", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(status = 'TERMINATED') = (termination_date IS NOT NULL)",
            name=op.f("ck_employees_terminated_has_date"),
        ),
        sa.CheckConstraint(
            "current_base_minor > 0", name=op.f("ck_employees_current_base_positive")
        ),
        sa.CheckConstraint(
            "current_total_minor >= current_base_minor",
            name=op.f("ck_employees_current_total_at_least_base"),
        ),
        sa.CheckConstraint(
            "termination_date >= hire_date", name=op.f("ck_employees_terminated_after_hire")
        ),
        sa.ForeignKeyConstraint(
            ["country_code"], ["countries.code"], name=op.f("fk_employees_country_code_countries")
        ),
        # employees and salary_records reference each other. SQLite takes this forward
        # reference inline; elsewhere CREATE TABLE leaves a use_alter constraint out, and it is
        # added below once salary_records exists.
        sa.ForeignKeyConstraint(
            ["current_salary_record_id"],
            ["salary_records.id"],
            name=op.f(CURRENT_SALARY_RECORD_FK),
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"], ["job_roles.id"], name=op.f("fk_employees_job_role_id_job_roles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employees")),
        sa.UniqueConstraint("email", name=op.f("uq_employees_email")),
        sa.UniqueConstraint("employee_code", name=op.f("uq_employees_employee_code")),
    )
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.create_index(
            "ix_employees_country_status", ["country_code", "status"], unique=False
        )
        batch_op.create_index(
            "ix_employees_currency_base", ["currency", "current_base_minor"], unique=False
        )
        batch_op.create_index("ix_employees_job_role_level", ["job_role_id", "level"], unique=False)
        batch_op.create_index("ix_employees_last_first", ["last_name", "first_name"], unique=False)
        batch_op.create_index(
            "ix_employees_status_employment_type", ["status", "employment_type"], unique=False
        )

    op.create_table(
        "salary_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("base_minor", sa.BigInteger(), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False),
        sa.Column("job_role_id", sa.Integer(), nullable=False),
        sa.Column(
            "level",
            sa.Enum(
                "L1",
                "L2",
                "L3",
                "L4",
                "L5",
                "L6",
                name="level",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Enum(
                "HIRE",
                "PROMOTION",
                "MERIT",
                "MARKET_ADJUSTMENT",
                "CORRECTION",
                name="reason",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("base_minor > 0", name=op.f("ck_salary_records_base_positive")),
        sa.CheckConstraint(
            "total_minor >= base_minor", name=op.f("ck_salary_records_total_at_least_base")
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"], ["users.id"], name=op.f("fk_salary_records_changed_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name=op.f("fk_salary_records_employee_id_employees")
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"], ["job_roles.id"], name=op.f("fk_salary_records_job_role_id_job_roles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_salary_records")),
    )
    with op.batch_alter_table("salary_records", schema=None) as batch_op:
        batch_op.create_index(
            "ix_salary_records_effective_reason", ["effective_date", "reason"], unique=False
        )
        batch_op.create_index(
            "ix_salary_records_employee_effective",
            ["employee_id", "effective_date", "id"],
            unique=False,
        )
    if _supports_alter_constraint():
        op.create_foreign_key(
            CURRENT_SALARY_RECORD_FK,
            "employees",
            "salary_records",
            ["current_salary_record_id"],
            ["id"],
        )

    op.create_table(
        "salary_components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("salary_record_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "ALLOWANCE",
                "BONUS_TARGET",
                name="component_type",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "amount_minor >= 0", name=op.f("ck_salary_components_amount_not_negative")
        ),
        sa.ForeignKeyConstraint(
            ["salary_record_id"],
            ["salary_records.id"],
            name=op.f("fk_salary_components_salary_record_id_salary_records"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_salary_components")),
        sa.UniqueConstraint(
            "salary_record_id", "type", "name", name="uq_salary_components_record_type_name"
        ),
    )
    with op.batch_alter_table("salary_components", schema=None) as batch_op:
        batch_op.create_index("ix_salary_components_record", ["salary_record_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("salary_components", schema=None) as batch_op:
        batch_op.drop_index("ix_salary_components_record")

    op.drop_table("salary_components")
    if _supports_alter_constraint():
        op.drop_constraint(CURRENT_SALARY_RECORD_FK, "employees", type_="foreignkey")
    with op.batch_alter_table("salary_records", schema=None) as batch_op:
        batch_op.drop_index("ix_salary_records_employee_effective")
        batch_op.drop_index("ix_salary_records_effective_reason")

    op.drop_table("salary_records")
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_index("ix_employees_status_employment_type")
        batch_op.drop_index("ix_employees_last_first")
        batch_op.drop_index("ix_employees_job_role_level")
        batch_op.drop_index("ix_employees_currency_base")
        batch_op.drop_index("ix_employees_country_status")

    op.drop_table("employees")
