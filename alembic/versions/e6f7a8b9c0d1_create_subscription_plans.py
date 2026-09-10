"""create subscription plans and user subscriptions

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-09-10 14:51:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("daily_journal_limit", sa.Integer(), nullable=True),
        sa.Column("weekly_summary_limit", sa.Integer(), nullable=True),
        sa.Column("daily_analyze_limit", sa.Integer(), nullable=True),
        sa.Column("weekly_insights_limit", sa.Integer(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("price_inr", sa.Integer(), nullable=True),
        sa.Column("billing_period", sa.String(length=32), nullable=True),
        sa.Column("cashfree_plan_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscription_plans")),
        sa.UniqueConstraint("code", name="uq_subscription_plans_code"),
    )
    with op.batch_alter_table("subscription_plans", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_subscription_plans_code"), ["code"], unique=False)

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("payment_provider", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("cashfree_customer_id", sa.String(length=128), nullable=True),
        sa.Column("cashfree_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("cashfree_order_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            name=op.f("fk_user_subscriptions_plan_id_subscription_plans"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_subscriptions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_subscriptions")),
        sa.UniqueConstraint("user_id", name="uq_user_subscriptions_user_id"),
    )
    with op.batch_alter_table("user_subscriptions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_subscriptions_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_user_subscriptions_plan_id"), ["plan_id"], unique=False)

    plans = sa.table(
        "subscription_plans",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("daily_journal_limit", sa.Integer),
        sa.column("weekly_summary_limit", sa.Integer),
        sa.column("daily_analyze_limit", sa.Integer),
        sa.column("weekly_insights_limit", sa.Integer),
        sa.column("is_default", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("price_inr", sa.Integer),
        sa.column("billing_period", sa.String),
    )
    op.bulk_insert(
        plans,
        [
            {
                "code": "free",
                "name": "Free",
                "description": "Default plan with daily and weekly caps.",
                "daily_journal_limit": 3,
                "weekly_summary_limit": 1,
                "daily_analyze_limit": 5,
                "weekly_insights_limit": 1,
                "is_default": True,
                "is_active": True,
                "sort_order": 0,
                "price_inr": 0,
                "billing_period": "monthly",
            },
            {
                "code": "pro",
                "name": "Pro",
                "description": "Unlimited journaling and AI actions.",
                "daily_journal_limit": None,
                "weekly_summary_limit": None,
                "daily_analyze_limit": None,
                "weekly_insights_limit": None,
                "is_default": False,
                "is_active": True,
                "sort_order": 10,
                "price_inr": 499,
                "billing_period": "monthly",
            },
        ],
    )

    # Assign Free to every existing user without a subscription.
    conn = op.get_bind()
    free_id = conn.execute(
        sa.text("SELECT id FROM subscription_plans WHERE code = 'free'")
    ).scalar_one()
    user_ids = conn.execute(sa.text("SELECT id FROM users")).scalars().all()
    if user_ids:
        subs = sa.table(
            "user_subscriptions",
            sa.column("user_id", sa.Integer),
            sa.column("plan_id", sa.Integer),
            sa.column("status", sa.String),
            sa.column("payment_provider", sa.String),
        )
        op.bulk_insert(
            subs,
            [
                {
                    "user_id": uid,
                    "plan_id": free_id,
                    "status": "active",
                    "payment_provider": "manual",
                }
                for uid in user_ids
            ],
        )


def downgrade() -> None:
    with op.batch_alter_table("user_subscriptions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_subscriptions_plan_id"))
        batch_op.drop_index(batch_op.f("ix_user_subscriptions_user_id"))
    op.drop_table("user_subscriptions")
    with op.batch_alter_table("subscription_plans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_subscription_plans_code"))
    op.drop_table("subscription_plans")
