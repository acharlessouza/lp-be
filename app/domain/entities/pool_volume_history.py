from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PoolVolumeHistoryPoint:
    time: str
    value: Decimal
    fees_usd: Decimal


@dataclass(frozen=True)
class PoolVolumeHistorySummaryBase:
    tvl_usd: Decimal | None
    avg_daily_fees_usd: Decimal | None
    avg_daily_volume_usd: Decimal | None
    token0_symbol: str | None
    token1_symbol: str | None


@dataclass(frozen=True)
class PoolVolumeHistorySummaryPremium:
    price_volatility_pct: Decimal | None
    correlation: Decimal | None
    geometric_mean_price: Decimal | None
