"""Billing endpoints: public plans, Cashfree checkout, webhook."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.billing import (
    BillingMeResponse,
    CreateCashfreeOrderRequest,
    CreateCashfreeOrderResponse,
    PlanSummary,
)
from app.services import billing_service, cashfree_client, cashfree_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanSummary], summary="List active subscription plans")
def list_plans(db: Session = Depends(get_db)) -> list[PlanSummary]:
    plans = cashfree_service.list_public_plans(db)
    return [billing_service.to_plan_summary(p) for p in plans]  # type: ignore[misc]


@router.get("/me", response_model=BillingMeResponse, summary="Current billing / payment status")
def billing_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingMeResponse:
    return BillingMeResponse(**cashfree_service.get_billing_me(db, current_user))


@router.post(
    "/cashfree/create-order",
    response_model=CreateCashfreeOrderResponse,
    summary="Start Cashfree checkout for a paid plan",
)
def create_cashfree_order(
    payload: CreateCashfreeOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CreateCashfreeOrderResponse:
    result = cashfree_service.create_checkout_session(
        db,
        current_user,
        plan_code=payload.plan_code,
        customer_phone=payload.customer_phone,
    )
    return CreateCashfreeOrderResponse(**result)


@router.post(
    "/cashfree/webhook",
    summary="Cashfree payment webhook (no JWT — signature verified)",
)
async def cashfree_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_signature: str | None = Header(default=None, alias="x-webhook-signature"),
    x_webhook_timestamp: str | None = Header(default=None, alias="x-webhook-timestamp"),
) -> dict:
    raw = (await request.body()).decode("utf-8")
    if not cashfree_client.verify_webhook_signature(
        signature=x_webhook_signature or "",
        timestamp=x_webhook_timestamp or "",
        raw_body=raw,
    ):
        raise ForbiddenError("Invalid Cashfree webhook signature")

    import json

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ForbiddenError("Invalid webhook JSON") from exc

    return cashfree_service.handle_payment_webhook(
        db, payload if isinstance(payload, dict) else {}
    )
