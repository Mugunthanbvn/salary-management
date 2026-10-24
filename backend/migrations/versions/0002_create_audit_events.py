"""create audit_events

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24 02:31:30.868242
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=40), nullable=True),
        sa.Column("diff", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_events_actor_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    with op.batch_alter_table("audit_events", schema=None) as batch_op:
        batch_op.create_index(
            "ix_audit_events_actor_action_at", ["actor_id", "action", "at"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_audit_events_at"), ["at"], unique=False)
        batch_op.create_index("ix_audit_events_entity", ["entity", "entity_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("audit_events", schema=None) as batch_op:
        batch_op.drop_index("ix_audit_events_entity")
        batch_op.drop_index(batch_op.f("ix_audit_events_at"))
        batch_op.drop_index("ix_audit_events_actor_action_at")

    op.drop_table("audit_events")
