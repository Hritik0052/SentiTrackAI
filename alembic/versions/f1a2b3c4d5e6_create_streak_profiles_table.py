"""create streak profiles table

Revision ID: f1a2b3c4d5e6
Revises: 8edd91e1be08
Create Date: 2026-09-09 16:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "8edd91e1be08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "streak_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("freeze_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("freezes_used_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_freeze_on", sa.Date(), nullable=True),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_entry_date", sa.Date(), nullable=True),
        sa.Column("freeze_earn_watermark", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_streak_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_streak_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_streak_profiles_user_id")),
    )
    with op.batch_alter_table("streak_profiles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_streak_profiles_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("streak_profiles", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_streak_profiles_user_id"))
    op.drop_table("streak_profiles")
