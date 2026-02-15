from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EstimateFeesInput:
    pool_id: int
    days: int
    min_price: Decimal
    max_price: Decimal
    deposit_usd: Decimal
    amount_token0: Decimal
    amount_token1: Decimal


@dataclass(frozen=True)
class EstimateFeesOutput:
    estimated_fees_24h: Decimal
    monthly_value: Decimal
    monthly_percent: Decimal
    yearly_value: Decimal
    yearly_apr: Decimal
