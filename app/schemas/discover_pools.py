from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class DiscoverPoolItem(BaseModel):
    pool_id: int
    pool_address: str
    pool_name: str
    network: str
    exchange: str
    fee_tier: int
    average_apr: Decimal
    price_volatility: Decimal | None
    tvl_usd: Decimal
    correlation: Decimal | None
    avg_daily_fees_usd: Decimal
    daily_fees_tvl_pct: Decimal
    avg_daily_volume_usd: Decimal
    daily_volume_tvl_pct: Decimal


class DiscoverPoolsResponse(BaseModel):
    page: int
    page_size: int
    total: int
    data: list[DiscoverPoolItem]
