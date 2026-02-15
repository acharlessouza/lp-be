from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class PoolPricePoint:
    timestamp: datetime
    price: Decimal


@dataclass(frozen=True)
class PoolPriceStats:
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None


@dataclass(frozen=True)
class PoolCurrentPrice:
    token1_price: Decimal | None
    token0_price: Decimal | None
    sqrt_price_x96: int | None
