from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EstimatedFeesPool:
    id: int
    token0_decimals: int
    token1_decimals: int


@dataclass(frozen=True)
class EstimatedFeesAggregates:
    pool_fees_in_range: Decimal | None
    avg_pool_liquidity_in_range: Decimal | None
    hours_in_range: int


@dataclass(frozen=True)
class EstimatedFeesBreakdown:
    estimated_fees_24h: Decimal
    monthly_value: Decimal
    monthly_percent: Decimal
    yearly_value: Decimal
    yearly_apr: Decimal
