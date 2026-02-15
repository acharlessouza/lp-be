from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MatchTicksPoolConfig:
    fee_tier: int


@dataclass(frozen=True)
class MatchTicksLatestPrices:
    token0_price: Decimal | None
    token1_price: Decimal | None
