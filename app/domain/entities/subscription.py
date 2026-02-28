from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


SubscriptionStatus = Literal[
    "trialing",
    "active",
    "past_due",
    "canceled",
    "unpaid",
    "incomplete",
    "incomplete_expired",
]


@dataclass(frozen=True)
class Subscription:
    id: str
    user_id: str
    plan_price_id: str
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    external_subscription_id: str | None
    created_at: datetime
    updated_at: datetime


def is_subscription_active(status: str) -> bool:
    return status in {"active", "trialing"}
