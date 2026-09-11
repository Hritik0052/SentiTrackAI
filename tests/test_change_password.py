"""Change password requires verifying the current password."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password, verify_password
from app.database import Base, get_db
from app.main import create_app
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import UserSubscription


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    free = SubscriptionPlan(
        code="free",
        name="Free",
        is_default=True,
        is_active=True,
        duration_days=15,
        billing_period="trial",
        price_inr=0,
        daily_journal_limit=3,
        weekly_summary_limit=1,
        daily_analyze_limit=5,
        weekly_insights_limit=1,
    )
    db.add(free)
    db.flush()
    user = User(
        name="Ada",
        email="ada@example.com",
        password_hash=hash_password("oldpass123"),
        is_admin=False,
    )
    db.add(user)
    db.flush()
    db.add(UserSubscription(user_id=user.id, plan_id=free.id, status="active"))
    db.commit()
    db.refresh(user)

    app = create_app()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c, db, user

    db.close()
    engine.dispose()


def test_change_password_success(client):
    c, db, user = client
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    bad = c.post(
        "/api/v1/users/me/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "newpass123"},
    )
    assert bad.status_code == 400

    ok = c.post(
        "/api/v1/users/me/change-password",
        headers=headers,
        json={"current_password": "oldpass123", "new_password": "newpass123"},
    )
    assert ok.status_code == 204
    db.refresh(user)
    assert verify_password("newpass123", user.password_hash)
