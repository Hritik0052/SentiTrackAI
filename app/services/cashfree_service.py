"""Cashfree checkout orchestration: create order + apply successful payments."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.models.user_subscription import UserSubscription
from app.schemas.billing import PlanSummary
from app.services import billing_service, cashfree_client


def list_public_plans(db: Session) -> list[SubscriptionPlan]:
    return billing_service.list_plans(db, active_only=True)


def get_upgrade_plan(db: Session, plan_code: str = "pro") -> SubscriptionPlan:
    plan = db.scalar(
        select(SubscriptionPlan).where(
            SubscriptionPlan.code == plan_code,
            SubscriptionPlan.is_active.is_(True),
        )
    )
    if plan is None:
        raise NotFoundError(f"Plan '{plan_code}' not found")
    if plan.price_inr is None or plan.price_inr <= 0:
        raise BadRequestError("This plan is not available for self-serve checkout")
    return plan


def create_checkout_session(
    db: Session,
    user: User,
    *,
    plan_code: str = "pro",
    customer_phone: str | None = None,
) -> dict:
    if not settings.cashfree_configured:
        raise BadRequestError(
            "Payments are not configured yet. Ask the admin to set Cashfree keys on the server."
        )

    plan = get_upgrade_plan(db, plan_code)
    current = billing_service.get_user_plan(db, user.id)
    if current is not None and current.id == plan.id:
        raise BadRequestError(f"You are already on the {plan.name} plan")

    phone = (customer_phone or "").strip() or "9999999999"
    if not phone.isdigit() or len(phone) < 10:
        raise BadRequestError("Enter a valid 10-digit mobile number for checkout")

    order_id = cashfree_client.make_order_id(user.id, plan.id)
    return_url = settings.cashfree_return_url
    if "{order_id}" not in return_url:
        sep = "&" if "?" in return_url else "?"
        return_url = f"{return_url}{sep}order_id={{order_id}}"

    cf_order = cashfree_client.create_order(
        order_id=order_id,
        amount_inr=float(plan.price_inr),
        customer_id=f"user_{user.id}",
        customer_email=user.email,
        customer_phone=phone[-10:],
        customer_name=user.name,
        return_url=return_url,
        order_tags={
            "user_id": str(user.id),
            "plan_id": str(plan.id),
            "plan_code": plan.code,
        },
    )

    sub = billing_service.get_user_subscription(db, user.id)
    if sub is None:
        sub = billing_service.assign_default_plan(db, user, commit=False)
    sub.cashfree_order_id = order_id
    sub.cashfree_customer_id = f"user_{user.id}"
    db.commit()

    return {
        "order_id": order_id,
        "payment_session_id": cf_order["payment_session_id"],
        "order_amount": float(plan.price_inr),
        "order_currency": "INR",
        "env": "production" if settings.cashfree_env.lower() == "production" else "sandbox",
        "plan": billing_service.to_plan_summary(plan),
    }


def activate_paid_plan(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
    order_id: str,
) -> UserSubscription:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    plan = billing_service.get_plan(db, plan_id)

    sub = billing_service.assign_plan(
        db,
        user,
        plan,
        notes=f"Cashfree order {order_id}",
        status="active",
        commit=False,
    )
    sub.payment_provider = "cashfree"
    sub.cashfree_order_id = order_id
    sub.cashfree_customer_id = sub.cashfree_customer_id or f"user_{user.id}"
    db.commit()
    db.refresh(sub)
    return sub


def handle_payment_webhook(db: Session, payload: dict) -> dict:
    event_type = str(payload.get("type") or "")
    data = payload.get("data") or {}
    order = data.get("order") or {}
    payment = data.get("payment") or {}

    order_id = str(order.get("order_id") or payment.get("order_id") or "")
    payment_status = str(payment.get("payment_status") or "").upper()

    if not order_id:
        return {"ok": True, "ignored": True, "reason": "missing_order_id"}

    if event_type not in {"PAYMENT_SUCCESS_WEBHOOK", "PAYMENT_SUCCESS"} and payment_status != "SUCCESS":
        return {"ok": True, "ignored": True, "reason": "not_success", "type": event_type}

    parsed = cashfree_client.parse_order_id(order_id)
    user_id = None
    plan_id = None
    if parsed:
        user_id, plan_id = parsed
    else:
        tags = order.get("order_tags") or {}
        try:
            user_id = int(tags.get("user_id"))
            plan_id = int(tags.get("plan_id"))
        except (TypeError, ValueError):
            pass

    if user_id is None or plan_id is None:
        # Fallback: confirm we created this order, then require parseable order_id.
        sub = db.scalar(
            select(UserSubscription).where(UserSubscription.cashfree_order_id == order_id)
        )
        if sub is None:
            return {"ok": True, "ignored": True, "reason": "unknown_order"}
        parsed = cashfree_client.parse_order_id(order_id)
        if parsed is None:
            return {"ok": True, "ignored": True, "reason": "unparseable_order"}
        user_id, plan_id = parsed

    activate_paid_plan(db, user_id=user_id, plan_id=plan_id, order_id=order_id)
    return {"ok": True, "upgraded": True, "user_id": user_id, "plan_id": plan_id, "order_id": order_id}


def get_billing_me(db: Session, user: User) -> dict:
    sub = billing_service.get_user_subscription(db, user.id)
    plan = sub.plan if sub else None
    return {
        "plan": billing_service.to_plan_summary(plan) if plan else None,
        "status": sub.status if sub else None,
        "payment_provider": sub.payment_provider if sub else None,
        "cashfree_order_id": sub.cashfree_order_id if sub else None,
        "cashfree_configured": settings.cashfree_configured,
        "cashfree_env": "production"
        if settings.cashfree_env.lower() == "production"
        else "sandbox",
    }
