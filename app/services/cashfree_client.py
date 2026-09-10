"""Cashfree Payments HTTP client + webhook signature helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import AIServiceError, BadRequestError


class CashfreeError(BadRequestError):
    detail = "Cashfree payment error"


def _headers() -> dict[str, str]:
    if not settings.cashfree_configured:
        raise CashfreeError("Cashfree is not configured. Set CASHFREE_APP_ID and CASHFREE_SECRET_KEY.")
    return {
        "Content-Type": "application/json",
        "x-client-id": settings.cashfree_app_id,
        "x-client-secret": settings.cashfree_secret_key,
        "x-api-version": settings.cashfree_api_version,
    }


def make_order_id(user_id: int, plan_id: int) -> str:
    # Cashfree order_id max length is typically 50; keep compact and parseable.
    return f"st_{user_id}_{plan_id}_{uuid.uuid4().hex[:10]}"


def parse_order_id(order_id: str) -> tuple[int, int] | None:
    try:
        parts = order_id.split("_")
        if len(parts) < 4 or parts[0] != "st":
            return None
        return int(parts[1]), int(parts[2])
    except (TypeError, ValueError):
        return None


def verify_webhook_signature(*, signature: str, timestamp: str, raw_body: str) -> bool:
    secret = settings.cashfree_signing_secret
    if not secret or not signature or not timestamp:
        return False
    signed = timestamp + raw_body
    digest = hmac.new(secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def create_order(
    *,
    order_id: str,
    amount_inr: float,
    customer_id: str,
    customer_email: str,
    customer_phone: str,
    customer_name: str,
    return_url: str,
    order_tags: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "order_id": order_id,
        "order_amount": round(float(amount_inr), 2),
        "order_currency": "INR",
        "customer_details": {
            "customer_id": customer_id,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "customer_name": customer_name,
        },
        "order_meta": {
            "return_url": return_url,
            "notify_url": settings.cashfree_webhook_url,
        },
    }
    if order_tags:
        payload["order_tags"] = order_tags

    url = f"{settings.cashfree_api_base}/orders"
    try:
        response = httpx.post(url, headers=_headers(), json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        raise AIServiceError(f"Cashfree unreachable: {exc}") from exc

    data = response.json() if response.content else {}
    if response.status_code >= 400:
        message = data.get("message") or data.get("error") or response.text or "Cashfree order failed"
        raise CashfreeError(str(message))

    session_id = data.get("payment_session_id")
    if not session_id:
        raise CashfreeError("Cashfree did not return payment_session_id")
    return data
