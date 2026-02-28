from __future__ import annotations

from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    plan_price_id: str = Field(..., min_length=1)


class CreateCheckoutSessionResponse(BaseModel):
    checkout_session_id: str
    checkout_url: str


class StripeWebhookResponse(BaseModel):
    event_type: str
    handled: bool
