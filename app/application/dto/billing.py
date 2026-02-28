from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CreateCheckoutSessionInput:
    user_id: str
    plan_price_id: str
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class CreateCheckoutSessionOutput:
    checkout_session_id: str
    checkout_url: str


@dataclass(frozen=True)
class StripeWebhookInput:
    signature: str
    payload: bytes


@dataclass(frozen=True)
class StripeWebhookOutput:
    event_type: str
    handled: bool


@dataclass(frozen=True)
class StripeCheckoutSessionResult:
    id: str
    url: str


@dataclass(frozen=True)
class StripeSubscriptionEventData:
    subscription_id: str
    customer_id: str | None
    price_id: str | None
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None


@dataclass(frozen=True)
class StripeCheckoutCompletedEventData:
    user_id: str | None
    customer_id: str | None


@dataclass(frozen=True)
class StripeWebhookEvent:
    event_type: str
    subscription: StripeSubscriptionEventData | None
    checkout_completed: StripeCheckoutCompletedEventData | None
