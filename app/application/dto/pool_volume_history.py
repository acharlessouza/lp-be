from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GetPoolVolumeHistoryInput:
    pool_address: str
    days: int
    chain_id: int | None
    dex_id: int | None
    include_premium: bool = False
    exchange: str = "binance"
    symbol0: str | None = None
    symbol1: str | None = None


@dataclass(frozen=True)
class PoolVolumeHistoryPointOutput:
    time: str
    value: Decimal
    fees_usd: Decimal


@dataclass(frozen=True)
class PoolVolumeHistorySummaryOutput:
    tvl_usd: Decimal | None
    avg_daily_fees_usd: Decimal | None
    daily_fees_tvl_pct: Decimal | None
    avg_daily_volume_usd: Decimal | None
    daily_volume_tvl_pct: Decimal | None
    price_volatility_pct: Decimal | None
    correlation: Decimal | None
    geometric_mean_price: Decimal | None


@dataclass(frozen=True)
class GetPoolVolumeHistoryOutput:
    volume_history: list[PoolVolumeHistoryPointOutput]
    summary: PoolVolumeHistorySummaryOutput
