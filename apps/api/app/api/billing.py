"""Stripe billing API — checkout, portal, webhook."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import get_db
from shared.models.subscription import UserSubscription
from app.auth import get_current_user

logger = logging.getLogger("reelsmaker.billing")
router = APIRouter()

TIER_LIMITS = {
    "free": {"max_projects": 3, "max_generations_per_month": 50},
    "pro": {"max_projects": 20, "max_generations_per_month": 500},
    "premium": {"max_projects": 100, "max_generations_per_month": 5000},
}


def _get_stripe():
    try:
        import stripe
    except ImportError:
        raise HTTPException(500, "stripe package not installed")
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Stripe not configured")
    stripe.api_key = settings.stripe_secret_key
    return stripe


async def _get_or_create_subscription(
    user_id: str, db: AsyncSession,
) -> UserSubscription:
    result = await db.execute(
        select(UserSubscription).where(UserSubscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        sub = UserSubscription(user_id=user_id)
        db.add(sub)
        await db.flush()
        await db.refresh(sub)
    return sub


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    max_projects: int
    max_generations_per_month: int
    generations_used: int
    stripe_customer_id: str | None = None
    current_period_end: str | None = None


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    sub = await _get_or_create_subscription(user_id, db)
    return SubscriptionResponse(
        tier=sub.tier,
        status=sub.status,
        max_projects=sub.max_projects,
        max_generations_per_month=sub.max_generations_per_month,
        generations_used=sub.generations_used,
        stripe_customer_id=sub.stripe_customer_id,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
    )


class CheckoutRequest(BaseModel):
    tier: str  # "pro" | "premium"
    success_url: str
    cancel_url: str


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    stripe = _get_stripe()
    settings = get_settings()

    price_map = {
        "pro": settings.stripe_price_pro_monthly,
        "premium": settings.stripe_price_premium_monthly,
    }
    price_id = price_map.get(body.tier)
    if not price_id:
        raise HTTPException(400, f"Invalid tier: {body.tier}")

    sub = await _get_or_create_subscription(user_id, db)

    if not sub.stripe_customer_id:
        customer = stripe.Customer.create(metadata={"user_id": user_id})
        sub.stripe_customer_id = customer.id
        await db.flush()

    session = stripe.checkout.Session.create(
        customer=sub.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        metadata={"user_id": user_id, "tier": body.tier},
    )

    return {"checkout_url": session.url}


@router.post("/portal")
async def create_portal(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    stripe = _get_stripe()
    sub = await _get_or_create_subscription(user_id, db)

    if not sub.stripe_customer_id:
        raise HTTPException(400, "No billing account found")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=get_settings().cors_origins[0] if get_settings().cors_origins else "http://localhost:3000",
    )

    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events for subscription lifecycle."""
    stripe = _get_stripe()
    settings = get_settings()

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret,
        )
    except Exception as e:
        logger.warning("Stripe webhook verification failed: %s", e)
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type in (
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        await _handle_subscription_change(data, db)
    elif event_type == "invoice.paid":
        await _handle_invoice_paid(data, db)

    return {"received": True}


async def _handle_checkout_completed(data: dict, db: AsyncSession) -> None:
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    tier = data.get("metadata", {}).get("tier", "pro")

    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.stripe_customer_id == customer_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    limits = TIER_LIMITS.get(tier, TIER_LIMITS["pro"])
    sub.tier = tier
    sub.stripe_subscription_id = subscription_id
    sub.status = "active"
    sub.max_projects = limits["max_projects"]
    sub.max_generations_per_month = limits["max_generations_per_month"]
    sub.generations_used = 0
    await db.flush()


async def _handle_subscription_change(data: dict, db: AsyncSession) -> None:
    subscription_id = data.get("id")
    status = data.get("status")

    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    if status in ("canceled", "unpaid", "past_due"):
        sub.status = status
        if status == "canceled":
            limits = TIER_LIMITS["free"]
            sub.tier = "free"
            sub.max_projects = limits["max_projects"]
            sub.max_generations_per_month = limits["max_generations_per_month"]
    elif status == "active":
        sub.status = "active"

    period_end = data.get("current_period_end")
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    await db.flush()


async def _handle_invoice_paid(data: dict, db: AsyncSession) -> None:
    customer_id = data.get("customer")

    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.stripe_customer_id == customer_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return

    sub.generations_used = 0
    period_end = data.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    await db.flush()
