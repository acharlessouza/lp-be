from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.entities.pool_price import PoolPricePoint


@dataclass(frozen=True)
class GetPoolPriceInput:
    pool_id: int
    days: int | None = None
    start: datetime | None = None
    end: datetime | None = None


@dataclass(frozen=True)
class GetPoolPriceOutput:
    pool_id: int
    days: int
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None
    current_price: Decimal | None
    series: list[PoolPricePoint]
