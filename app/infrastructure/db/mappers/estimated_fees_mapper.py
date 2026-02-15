from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.estimated_fees import EstimatedFeesAggregates, EstimatedFeesPool


def map_row_to_estimated_fees_pool(row: Mapping[str, Any]) -> EstimatedFeesPool:
    return EstimatedFeesPool(
        id=row["id"],
        token0_decimals=row["token0_decimals"],
        token1_decimals=row["token1_decimals"],
    )


def map_row_to_estimated_fees_aggregates(row: Mapping[str, Any]) -> EstimatedFeesAggregates:
    return EstimatedFeesAggregates(
        pool_fees_in_range=Decimal(str(row["pool_fees_in_range"]))
        if row["pool_fees_in_range"] is not None
        else None,
        avg_pool_liquidity_in_range=Decimal(str(row["avg_pool_liquidity_in_range"]))
        if row["avg_pool_liquidity_in_range"] is not None
        else None,
        hours_in_range=int(row["hours_in_range"] or 0),
    )
