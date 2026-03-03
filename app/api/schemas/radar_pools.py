from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class RadarPoolResponseItem(BaseModel):
    pool_id: int
    pool_address: str
    pool_name: str
    network: str
    exchange: str
    dex_id: int
    chain_id: int
    token0_address: str
    token1_address: str
    token0_symbol: str
    token1_symbol: str
    token0_icon_url: str | None
    token1_icon_url: str | None
    fee_tier: int
    average_apr: Decimal
    price_volatility: Decimal | None
    tvl_usd: Decimal
    correlation: Decimal | None
    avg_daily_fees_usd: Decimal
    daily_fees_tvl_pct: Decimal
    avg_daily_volume_usd: Decimal
    daily_volume_tvl_pct: Decimal


class RadarPoolsResponse(BaseModel):
    page: int
    page_size: int
    total: int
    data: list[RadarPoolResponseItem]
