"""add allowed_values to import_jobs

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-24 06:33:31.142694
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("import_jobs", schema=None) as batch_op:
        # Jobs stored before this revision get an empty object.
        batch_op.add_column(
            sa.Column("allowed_values", sa.JSON(), nullable=False, server_default="{}")
        )


def downgrade() -> None:
    with op.batch_alter_table("import_jobs", schema=None) as batch_op:
        batch_op.drop_column("allowed_values")
