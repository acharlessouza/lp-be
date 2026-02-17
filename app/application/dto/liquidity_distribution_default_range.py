from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class GetLiquidityDistributionDefaultRangeInput:
    pool_id: int | str
    chain_id: int | None
    dex_id: int | None
    snapshot_date: date
    preset: str
    initial_price: Decimal | None
    center_tick: int | None
    swapped_pair: bool


@dataclass(frozen=True)
class GetLiquidityDistributionDefaultRangeOutput:
    min_price: float
    max_price: float
    min_tick: int
    max_tick: int
    tick_spacing: int
