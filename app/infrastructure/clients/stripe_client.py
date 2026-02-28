from __future__ import annotations

from datetime import datetime, timezone

import stripe

from app.application.dto.billing import (
    StripeCheckoutCompletedEventData,
    StripeCheckoutSessionResult,
    StripeSubscriptionEventData,
    StripeWebhookEvent,
)
from app.application.ports.stripe_port import StripePort
from app.domain.exceptions import BillingError


class StripeClient(StripePort):
    def __init__(self, *, secret_key: str, webhook_secret: str):
        stripe.api_key = secret_key
        self._webhook_secret = webhook_secret

    def create_customer(self, *, user_id: str, email: str, name: str) -> str:
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id},
            )
        except Exception as exc:  # pragma: no cover - external API
            raise BillingError("Failed to create Stripe customer.") from exc

        customer_id = getattr(customer, "id", None)
        if not customer_id:
            raise BillingError("Stripe customer id is missing.")
        return str(customer_id)

    def create_checkout_session(
        self,
        *,
        user_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        customer_id: str | None,
        customer_email: str | None,
    ) -> StripeCheckoutSessionResult:
        payload: dict = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": user_id,
            "metadata": {"user_id": user_id},
        }
        if customer_id:
            payload["customer"] = customer_id
        elif customer_email:
            payload["customer_email"] = customer_email

        try:
            session = stripe.checkout.Session.create(**payload)
        except Exception as exc:  # pragma: no cover - external API
            raise BillingError("Failed to create Stripe checkout session.") from exc

        session_id = getattr(session, "id", None)
        session_url = getattr(session, "url", None)
        if not session_id or not session_url:
            raise BillingError("Stripe checkout session response is incomplete.")

        return StripeCheckoutSessionResult(id=str(session_id), url=str(session_url))

    def verify_webhook(self, *, signature: str, payload: bytes) -> StripeWebhookEvent:
        try:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=self._webhook_secret)
        except Exception as exc:  # pragma: no cover - external API
            raise BillingError("Invalid Stripe webhook signature.") from exc

        event_type = str(event.get("type", ""))
        data_object = event.get("data", {}).get("object", {})

        if event_type.startswith("customer.subscription."):
            price_id = None
            items = data_object.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id")
            return StripeWebhookEvent(
                event_type=event_type,
                subscription=StripeSubscriptionEventData(
                    subscription_id=str(data_object.get("id")),
                    customer_id=data_object.get("customer"),
                    price_id=price_id,
                    status=str(data_object.get("status")),
                    current_period_start=_to_datetime(data_object.get("current_period_start")),
                    current_period_end=_to_datetime(data_object.get("current_period_end")),
                    cancel_at_period_end=bool(data_object.get("cancel_at_period_end", False)),
                    canceled_at=_to_datetime(data_object.get("canceled_at")),
                ),
                checkout_completed=None,
            )

        if event_type == "checkout.session.completed":
            return StripeWebhookEvent(
                event_type=event_type,
                subscription=None,
                checkout_completed=StripeCheckoutCompletedEventData(
                    user_id=data_object.get("client_reference_id"),
                    customer_id=data_object.get("customer"),
                ),
            )

        return StripeWebhookEvent(
            event_type=event_type,
            subscription=None,
            checkout_completed=None,
        )


def _to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc)
