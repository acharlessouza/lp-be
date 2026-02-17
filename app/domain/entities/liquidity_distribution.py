from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class LiquidityDistributionPool:
    id: int
    token0_symbol: str
    token1_symbol: str
    token0_decimals: int
    token1_decimals: int
    fee_tier: int | None
    tick_spacing: int | None
    pool_tick: int | None
    current_tick: int | None
    current_price_token1_per_token0: Decimal | None
    onchain_liquidity: Decimal | None


@dataclass(frozen=True)
class TickLiquidity:
    tick_idx: int
    liquidity_net: Decimal


@dataclass(frozen=True)
class LiquidityDistributionSnapshot:
    period_start: datetime
