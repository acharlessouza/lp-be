from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.pool_price import PoolCurrentPrice, PoolPricePoint, PoolPriceStats


def map_row_to_pool_price_point(row: Mapping[str, Any]) -> PoolPricePoint:
    return PoolPricePoint(
        timestamp=row["timestamp"],
        price=Decimal(str(row["price"])),
    )


def map_row_to_pool_price_stats(row: Mapping[str, Any]) -> PoolPriceStats:
    return PoolPriceStats(
        min_price=Decimal(str(row["min_price"])) if row["min_price"] is not None else None,
        max_price=Decimal(str(row["max_price"])) if row["max_price"] is not None else None,
        avg_price=Decimal(str(row["avg_price"])) if row["avg_price"] is not None else None,
    )


def map_row_to_current_pool_price(row: Mapping[str, Any]) -> PoolCurrentPrice:
    return PoolCurrentPrice(
        token1_price=Decimal(str(row["token1_price"])) if row["token1_price"] is not None else None,
        token0_price=Decimal(str(row["token0_price"])) if row["token0_price"] is not None else None,
        sqrt_price_x96=int(row["sqrt_price_x96"]) if row["sqrt_price_x96"] is not None else None,
    )
