from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.pool_volume_history import (
    PoolVolumeHistoryPoint,
    PoolVolumeHistorySummaryBase,
    PoolVolumeHistorySummaryPremium,
)


def map_row_to_pool_volume_history_point(row: Mapping[str, Any]) -> PoolVolumeHistoryPoint:
    raw_time = row["time"]
    return PoolVolumeHistoryPoint(
        time=str(raw_time),
        value=Decimal(str(row["value"])) if row["value"] is not None else Decimal("0"),
        fees_usd=Decimal(str(row["fees_usd"])) if row["fees_usd"] is not None else Decimal("0"),
    )


def map_row_to_pool_volume_history_summary_base(row: Mapping[str, Any]) -> PoolVolumeHistorySummaryBase:
    return PoolVolumeHistorySummaryBase(
        tvl_usd=Decimal(str(row["tvl_usd"])) if row.get("tvl_usd") is not None else None,
        avg_daily_fees_usd=Decimal(str(row["avg_daily_fees_usd"]))
        if row.get("avg_daily_fees_usd") is not None
        else None,
        avg_daily_volume_usd=Decimal(str(row["avg_daily_volume_usd"]))
        if row.get("avg_daily_volume_usd") is not None
        else None,
        token0_symbol=str(row["token0_symbol"]) if row.get("token0_symbol") is not None else None,
        token1_symbol=str(row["token1_symbol"]) if row.get("token1_symbol") is not None else None,
    )


def map_row_to_pool_volume_history_summary_premium(
    row: Mapping[str, Any],
) -> PoolVolumeHistorySummaryPremium:
    return PoolVolumeHistorySummaryPremium(
        price_volatility_pct=Decimal(str(row["price_volatility_pct"]))
        if row.get("price_volatility_pct") is not None
        else None,
        correlation=Decimal(str(row["correlation"])) if row.get("correlation") is not None else None,
        geometric_mean_price=Decimal(str(row["geometric_mean_price"]))
        if row.get("geometric_mean_price") is not None
        else None,
    )
