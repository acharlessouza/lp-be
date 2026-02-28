from __future__ import annotations

from app.application.dto.billing import StripeWebhookInput, StripeWebhookOutput
from app.application.ports.auth_port import AuthPort
from app.application.ports.entitlements_port import EntitlementsPort
from app.application.ports.stripe_port import StripePort
from app.domain.exceptions import BillingError

from .auth_common import utcnow


class ProcessStripeWebhookUseCase:
    def __init__(
        self,
        *,
        auth_port: AuthPort,
        entitlements_port: EntitlementsPort,
        stripe_port: StripePort,
    ):
        self._auth_port = auth_port
        self._entitlements_port = entitlements_port
        self._stripe_port = stripe_port

    def execute(self, command: StripeWebhookInput) -> StripeWebhookOutput:
        event = self._stripe_port.verify_webhook(signature=command.signature, payload=command.payload)

        if event.event_type == "checkout.session.completed" and event.checkout_completed is not None:
            if event.checkout_completed.user_id and event.checkout_completed.customer_id:
                self._auth_port.update_user_stripe_customer_id(
                    user_id=event.checkout_completed.user_id,
                    stripe_customer_id=event.checkout_completed.customer_id,
                )
            return StripeWebhookOutput(event_type=event.event_type, handled=True)

        if event.event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            subscription = event.subscription
            if subscription is None:
                raise BillingError("Stripe subscription event missing payload.")
            if not subscription.customer_id:
                raise BillingError("Stripe subscription event missing customer id.")

            user = self._auth_port.get_user_by_stripe_customer_id(
                stripe_customer_id=subscription.customer_id
            )
            if user is None:
                raise BillingError("No user linked to Stripe customer id.")

            if event.event_type == "customer.subscription.deleted":
                self._entitlements_port.cancel_subscription_by_external_id(
                    subscription_id=subscription.subscription_id,
                    status=subscription.status,
                    canceled_at=subscription.canceled_at,
                    now=utcnow(),
                )
                return StripeWebhookOutput(event_type=event.event_type, handled=True)

            if not subscription.price_id:
                raise BillingError("Stripe subscription event missing price id.")

            plan_price = self._entitlements_port.get_plan_price_by_external_price_id(
                external_price_id=subscription.price_id,
            )
            if plan_price is None:
                raise BillingError("Stripe price not mapped to plan_prices.external_price_id.")

            self._entitlements_port.upsert_subscription_by_external_id(
                subscription_id=subscription.subscription_id,
                user_id=user.id,
                plan_price_id=plan_price.id,
                status=subscription.status,
                current_period_start=subscription.current_period_start,
                current_period_end=subscription.current_period_end,
                cancel_at_period_end=subscription.cancel_at_period_end,
                canceled_at=subscription.canceled_at,
                now=utcnow(),
            )
            return StripeWebhookOutput(event_type=event.event_type, handled=True)

        if event.event_type in {"invoice.paid", "invoice.payment_failed"}:
            return StripeWebhookOutput(event_type=event.event_type, handled=True)

        return StripeWebhookOutput(event_type=event.event_type, handled=False)
