from __future__ import annotations

from typing import Protocol

from app.application.dto.billing import StripeCheckoutSessionResult, StripeWebhookEvent


class StripePort(Protocol):
    def create_customer(self, *, user_id: str, email: str, name: str) -> str:
        ...

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
        ...

    def verify_webhook(self, *, signature: str, payload: bytes) -> StripeWebhookEvent:
        ...
