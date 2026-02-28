from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    code: str
    name: str
    description: str | None
    is_active: bool
    sort_order: int


@dataclass(frozen=True)
class PlanPrice:
    id: str
    plan_id: str
    interval: str
    currency: str
    amount_cents: int
    is_active: bool
    external_price_id: str | None
