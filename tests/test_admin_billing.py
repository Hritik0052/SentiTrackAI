"""Smoke tests for admin auth, plans seed, quotas, and /users/me plan fields."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import create_app
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.services import billing_service


def _seed_plans(db):
    free = SubscriptionPlan(
        code="free",
        name="Free",
        description="Free",
        daily_journal_limit=2,
        weekly_summary_limit=1,
        daily_analyze_limit=2,
        weekly_insights_limit=1,
        is_default=True,
        is_active=True,
        sort_order=0,
        price_inr=0,
        billing_period="trial",
        duration_days=15,
    )
    pro = SubscriptionPlan(
        code="pro",
        name="Pro",
        description="Pro",
        daily_journal_limit=None,
        weekly_summary_limit=None,
        daily_analyze_limit=None,
        weekly_insights_limit=None,
        is_default=False,
        is_active=True,
        sort_order=10,
        price_inr=499,
        billing_period="monthly",
        duration_days=30,
    )
    db.add_all([free, pro])
    db.flush()
    return free, pro


@pytest.fixture()
def admin_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    free, pro = _seed_plans(db)

    admin = User(
        name="Admin",
        email="admin@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    member = User(
        name="Member",
        email="member@example.com",
        password_hash=hash_password("password123"),
        is_admin=False,
    )
    db.add_all([admin, member])
    db.flush()
    db.add_all(
        [
            UserSubscription(user_id=admin.id, plan_id=free.id, status="active"),
            UserSubscription(user_id=member.id, plan_id=free.id, status="active"),
        ]
    )
    db.commit()
    db.refresh(admin)
    db.refresh(member)

    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        yield client, db, admin, member, free, pro
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_me_includes_is_admin_and_plan(admin_client):
    client, _db, admin, _member, _free, _pro = admin_client
    token = create_access_token(admin.id)
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_admin"] is True
    assert body["plan"]["code"] == "free"


def test_non_admin_cannot_access_admin_stats(admin_client):
    client, _db, _admin, member, _free, _pro = admin_client
    token = create_access_token(member.id)
    response = client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_stats_and_plans(admin_client):
    client, _db, admin, _member, _free, _pro = admin_client
    token = create_access_token(admin.id)
    headers = {"Authorization": f"Bearer {token}"}

    stats = client.get("/api/v1/admin/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.json()["total_users"] == 2

    plans = client.get("/api/v1/admin/plans", headers=headers)
    assert plans.status_code == 200
    assert {p["code"] for p in plans.json()} == {"free", "pro"}


def test_journal_quota_blocks_after_limit(admin_client):
    client, db, _admin, member, _free, _pro = admin_client
    token = create_access_token(member.id)
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(2):
        response = client.post(
            "/api/v1/journals",
            headers=headers,
            json={"title": f"Entry {i}", "content": "hello world content"},
        )
        assert response.status_code == 201, response.text

    blocked = client.post(
        "/api/v1/journals",
        headers=headers,
        json={"title": "Too many", "content": "should fail"},
    )
    assert blocked.status_code == 400
    assert "limit reached" in blocked.json()["error"]["detail"].lower()

    usage = client.get("/api/v1/users/me/usage", headers=headers)
    assert usage.status_code == 200
    body = usage.json()
    assert body["journals_today"]["used"] == 2
    assert body["journals_today"]["remaining"] == 0


def test_admin_can_assign_pro(admin_client):
    client, _db, admin, member, _free, pro = admin_client
    admin_token = create_access_token(admin.id)
    member_token = create_access_token(member.id)

    patched = client.patch(
        f"/api/v1/admin/users/{member.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan_id": pro.id},
    )
    assert patched.status_code == 200
    assert patched.json()["plan"]["code"] == "pro"

    # After Pro, journal create should succeed beyond Free limit.
    headers = {"Authorization": f"Bearer {member_token}"}
    for i in range(3):
        response = client.post(
            "/api/v1/journals",
            headers=headers,
            json={"title": f"Pro {i}", "content": "unlimited-ish"},
        )
        assert response.status_code == 201, response.text


def test_require_quota_uses_default_when_missing_sub(admin_client):
    client, db, _admin, _member, free, _pro = admin_client
    orphan = User(
        name="Orphan",
        email="orphan@example.com",
        password_hash=hash_password("password123"),
    )
    db.add(orphan)
    db.commit()
    db.refresh(orphan)

    billing_service.require_quota(db, orphan.id, billing_service.ACTION_JOURNAL)
    sub = billing_service.get_user_subscription(db, orphan.id)
    assert sub is not None
    assert sub.plan_id == free.id
