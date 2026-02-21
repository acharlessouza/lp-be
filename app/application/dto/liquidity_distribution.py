from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class GetLiquidityDistributionInput:
    pool_id: int | str
    chain_id: int | None
    dex_id: int | None
    snapshot_date: date
    current_tick: int
    center_tick: int | None
    tick_range: int
    range_min: Decimal | None = None
    range_max: Decimal | None = None
    swapped_pair: bool = False


@dataclass(frozen=True)
class LiquidityDistributionPointOutput:
    tick: int
    liquidity: str
    price: float


@dataclass(frozen=True)
class GetLiquidityDistributionOutput:
    token0: str
    token1: str
    current_tick: int
    data: list[LiquidityDistributionPointOutput]
