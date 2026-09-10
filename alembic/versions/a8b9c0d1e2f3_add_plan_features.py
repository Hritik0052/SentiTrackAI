"""add features to subscription_plans

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-09-10 16:55:00.000000
"""

from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FREE_FEATURES = [
    "3 journal entries per day",
    "5 AI sentiment analyses per day",
    "1 weekly summary per week",
    "1 insights generation per week",
    "Mood trends & Excel export",
    "Achievements & streaks",
]

PRO_FEATURES = [
    "Unlimited journal entries",
    "Unlimited AI sentiment analysis",
    "Unlimited weekly summaries",
    "Unlimited insights",
    "Mood trends & Excel export",
    "Achievements & streaks",
    "Priority AI access",
]


def upgrade() -> None:
    with op.batch_alter_table("subscription_plans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("features", sa.JSON(), nullable=True))

    conn = op.get_bind()
    dialect = conn.dialect.name
    rows = conn.execute(sa.text("SELECT id, code FROM subscription_plans")).mappings().all()
    for row in rows:
        if row["code"] == "free":
            feats = FREE_FEATURES
        elif row["code"] == "pro":
            feats = PRO_FEATURES
        else:
            continue
        payload = json.dumps(feats)
        if dialect == "postgresql":
            conn.execute(
                sa.text(
                    "UPDATE subscription_plans SET features = CAST(:features AS jsonb) WHERE id = :id"
                ),
                {"features": payload, "id": row["id"]},
            )
        else:
            conn.execute(
                sa.text("UPDATE subscription_plans SET features = :features WHERE id = :id"),
                {"features": payload, "id": row["id"]},
            )


def downgrade() -> None:
    with op.batch_alter_table("subscription_plans", schema=None) as batch_op:
        batch_op.drop_column("features")
