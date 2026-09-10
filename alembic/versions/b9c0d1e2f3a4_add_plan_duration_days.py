"""add duration_days to subscription plans

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-09-10 17:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("subscription_plans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("duration_days", sa.Integer(), nullable=True))

    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE subscription_plans SET duration_days = 15, billing_period = 'trial' "
            "WHERE code = 'free'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE subscription_plans SET duration_days = 30, billing_period = 'monthly' "
            "WHERE code = 'pro'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE subscription_plans SET duration_days = 30 "
            "WHERE duration_days IS NULL AND COALESCE(billing_period, 'monthly') = 'monthly'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE subscription_plans SET duration_days = 365 "
            "WHERE duration_days IS NULL AND billing_period = 'yearly'"
        )
    )

    dialect = conn.dialect.name
    if dialect == "postgresql":
        conn.execute(
            sa.text(
                """
                UPDATE user_subscriptions AS us
                SET
                  starts_at = COALESCE(us.starts_at, us.created_at),
                  ends_at = COALESCE(us.starts_at, us.created_at)
                    + (COALESCE(sp.duration_days, 30) * INTERVAL '1 day')
                FROM subscription_plans AS sp
                WHERE us.plan_id = sp.id
                  AND us.ends_at IS NULL
                  AND us.status = 'active'
                """
            )
        )
    else:
        # SQLite / others: set ends_at in Python
        from datetime import datetime, timedelta

        rows = conn.execute(
            sa.text(
                """
                SELECT us.id AS sub_id, us.starts_at, us.created_at, sp.duration_days
                FROM user_subscriptions us
                JOIN subscription_plans sp ON sp.id = us.plan_id
                WHERE us.ends_at IS NULL AND us.status = 'active'
                """
            )
        ).mappings().all()
        for row in rows:
            start = row["starts_at"] or row["created_at"] or datetime.utcnow()
            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace("Z", ""))
            days = int(row["duration_days"] or 30)
            end = start + timedelta(days=days)
            conn.execute(
                sa.text(
                    "UPDATE user_subscriptions SET starts_at = :starts, ends_at = :ends WHERE id = :id"
                ),
                {"starts": start, "ends": end, "id": row["sub_id"]},
            )


def downgrade() -> None:
    with op.batch_alter_table("subscription_plans", schema=None) as batch_op:
        batch_op.drop_column("duration_days")
