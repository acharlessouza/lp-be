from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class PoolVolumeHistoryPointResponse(BaseModel):
    time: str
    value: Decimal
    fees_usd: Decimal


class PoolVolumeHistorySummaryResponse(BaseModel):
    tvl_usd: Decimal | None
    avg_daily_fees_usd: Decimal | None
    daily_fees_tvl_pct: Decimal | None
    avg_daily_volume_usd: Decimal | None
    daily_volume_tvl_pct: Decimal | None
    price_volatility_pct: Decimal | None
    correlation: Decimal | None
    geometric_mean_price: Decimal | None


class PoolVolumeHistoryWithSummaryResponse(BaseModel):
    volume_history: list[PoolVolumeHistoryPointResponse]
    summary: PoolVolumeHistorySummaryResponse
