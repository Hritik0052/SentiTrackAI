"""Cashfree webhook activates Pro plan after signed success event."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import create_app
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.services import cashfree_client, cashfree_service


@pytest.fixture()
def db_client(monkeypatch):
    monkeypatch.setattr(settings, "cashfree_app_id", "test_app")
    monkeypatch.setattr(settings, "cashfree_secret_key", "test_secret")
    monkeypatch.setattr(settings, "cashfree_webhook_secret", "")
    monkeypatch.setattr(settings, "cashfree_env", "sandbox")

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
        daily_journal_limit=3,
        weekly_summary_limit=1,
        daily_analyze_limit=5,
        weekly_insights_limit=1,
        is_default=True,
        is_active=True,
        price_inr=0,
    )
    pro = SubscriptionPlan(
        code="pro",
        name="Pro",
        daily_journal_limit=None,
        weekly_summary_limit=None,
        daily_analyze_limit=None,
        weekly_insights_limit=None,
        is_default=False,
        is_active=True,
        price_inr=499,
        billing_period="monthly",
    )
    db.add_all([free, pro])
    db.flush()
    user = User(
        name="Payer",
        email="payer@example.com",
        password_hash=hash_password("password123"),
        is_admin=False,
    )
    db.add(user)
    db.flush()
    db.add(UserSubscription(user_id=user.id, plan_id=free.id, status="active"))
    db.commit()
    db.refresh(user)
    db.refresh(pro)

    app = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client, db, user, free, pro
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_webhook_upgrades_to_pro(db_client):
    client, db, user, _free, pro = db_client
    order_id = cashfree_client.make_order_id(user.id, pro.id)
    sub = db.query(UserSubscription).filter_by(user_id=user.id).one()
    sub.cashfree_order_id = order_id
    db.commit()

    payload = {
        "type": "PAYMENT_SUCCESS_WEBHOOK",
        "data": {
            "order": {"order_id": order_id, "order_tags": {"user_id": str(user.id), "plan_id": str(pro.id)}},
            "payment": {"payment_status": "SUCCESS", "order_id": order_id},
        },
    }
    raw = json.dumps(payload, separators=(",", ":"))
    ts = "1710000000"
    sig = base64.b64encode(
        hmac.new(b"test_secret", (ts + raw).encode(), hashlib.sha256).digest()
    ).decode()

    response = client.post(
        "/api/v1/billing/cashfree/webhook",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "x-webhook-signature": sig,
            "x-webhook-timestamp": ts,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["upgraded"] is True

    db.refresh(sub)
    assert sub.plan_id == pro.id
    assert sub.payment_provider == "cashfree"


def test_billing_me_requires_auth(db_client):
    client, _db, _user, _free, _pro = db_client
    assert client.get("/api/v1/billing/me").status_code == 401


def test_billing_me_ok(db_client):
    client, _db, user, _free, _pro = db_client
    token = create_access_token(user.id)
    response = client.get(
        "/api/v1/billing/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cashfree_configured"] is True
    assert body["plan"]["code"] == "free"


def test_create_order_calls_cashfree(db_client, monkeypatch):
    client, _db, user, _free, pro = db_client

    def fake_create_order(**kwargs):
        assert kwargs["amount_inr"] == 499.0
        return {"payment_session_id": "session_test", "order_id": kwargs["order_id"]}

    monkeypatch.setattr(cashfree_client, "create_order", fake_create_order)
    # create_checkout_session imports create_order via cashfree_client module used inside service
    monkeypatch.setattr(
        "app.services.cashfree_service.cashfree_client.create_order",
        fake_create_order,
    )

    token = create_access_token(user.id)
    response = client.post(
        "/api/v1/billing/cashfree/create-order",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_code": "pro", "customer_phone": "9876543210"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["payment_session_id"] == "session_test"
    assert body["plan"]["code"] == "pro"
    assert body["env"] == "sandbox"
