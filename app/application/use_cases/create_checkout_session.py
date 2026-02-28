from __future__ import annotations

from app.application.dto.billing import CreateCheckoutSessionInput, CreateCheckoutSessionOutput
from app.application.ports.auth_port import AuthPort
from app.application.ports.entitlements_port import EntitlementsPort
from app.application.ports.stripe_port import StripePort
from app.domain.exceptions import BillingError


class CreateCheckoutSessionUseCase:
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

    def execute(self, command: CreateCheckoutSessionInput) -> CreateCheckoutSessionOutput:
        user = self._auth_port.get_user_by_id(user_id=command.user_id)
        if user is None:
            raise BillingError("User not found.")

        plan_price = self._entitlements_port.get_plan_price_by_id(plan_price_id=command.plan_price_id)
        if plan_price is None:
            raise BillingError("Plan price not found.")
        if not plan_price.external_price_id:
            raise BillingError("Plan price is missing Stripe external_price_id.")

        customer_id = user.stripe_customer_id
        if not customer_id:
            customer_id = self._stripe_port.create_customer(user_id=user.id, email=user.email, name=user.name)
            self._auth_port.update_user_stripe_customer_id(
                user_id=user.id,
                stripe_customer_id=customer_id,
            )

        result = self._stripe_port.create_checkout_session(
            user_id=user.id,
            price_id=plan_price.external_price_id,
            success_url=command.success_url,
            cancel_url=command.cancel_url,
            customer_id=customer_id,
            customer_email=user.email,
        )
        return CreateCheckoutSessionOutput(
            checkout_session_id=result.id,
            checkout_url=result.url,
        )
