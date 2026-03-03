from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RadarPoolsInput:
    network_id: int | None = None
    exchange_id: int | None = None
    token_symbol: str | None = None
    timeframe_days: int = 14
    page: int = 1
    page_size: int = 10
    order_by: str = "average_apr"
    order_dir: str = "desc"


@dataclass(frozen=True)
class RadarPoolOutputItem:
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


@dataclass(frozen=True)
class RadarPoolsOutput:
    page: int
    page_size: int
    total: int
    data: list[RadarPoolOutputItem]
