"""create reference tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-24 03:33:18.537404
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("code", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("default_currency", sa.CHAR(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "default_currency IN ('AUD', 'BRL', 'CAD', 'EUR', 'GBP', 'INR', 'JPY', 'SGD', 'USD')",
            name=op.f("ck_countries_default_currency_supported"),
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_countries")),
    )
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("name", name=op.f("uq_departments_name")),
    )
    op.create_table(
        "fx_rates",
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("rate_to_usd", sa.String(length=32), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_fx_rates_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("currency", name=op.f("pk_fx_rates")),
    )
    op.create_table(
        "job_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column(
            "family",
            sa.Enum(
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
                name="family",
                native_enum=False,
                create_constraint=True,
                length=30,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_job_roles_department_id_departments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_roles")),
        sa.UniqueConstraint("title", name=op.f("uq_job_roles_title")),
    )
    with op.batch_alter_table("job_roles", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_job_roles_department_id"), ["department_id"], unique=False
        )

    op.create_table(
        "pay_bands",
        sa.Column("id", sa.Integer(), nullable=False),
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
        sa.Column("country_code", sa.CHAR(length=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("min_minor", sa.BigInteger(), nullable=False),
        sa.Column("mid_minor", sa.BigInteger(), nullable=False),
        sa.Column("max_minor", sa.BigInteger(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.CheckConstraint("max_minor >= mid_minor", name=op.f("ck_pay_bands_max_at_least_mid")),
        sa.CheckConstraint("mid_minor >= min_minor", name=op.f("ck_pay_bands_mid_at_least_min")),
        sa.CheckConstraint("min_minor > 0", name=op.f("ck_pay_bands_min_positive")),
        sa.ForeignKeyConstraint(
            ["country_code"], ["countries.code"], name=op.f("fk_pay_bands_country_code_countries")
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"], ["job_roles.id"], name=op.f("fk_pay_bands_job_role_id_job_roles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pay_bands")),
        sa.UniqueConstraint(
            "job_role_id",
            "level",
            "country_code",
            "effective_from",
            name=op.f("uq_pay_bands_job_role_id_level_country_code_effective_from"),
        ),
    )


def downgrade() -> None:
    op.drop_table("pay_bands")
    with op.batch_alter_table("job_roles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_job_roles_department_id"))

    op.drop_table("job_roles")
    op.drop_table("fx_rates")
    op.drop_table("departments")
    op.drop_table("countries")
