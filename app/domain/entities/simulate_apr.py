from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class SimulateAprPool:
    dex_id: int
    chain_id: int
    pool_address: str
    token0_decimals: int
    token1_decimals: int
    fee_tier: int | None
    tick_spacing: int | None


@dataclass(frozen=True)
class SimulateAprPoolState:
    tick: int | None
    sqrt_price_x96: int | None
    liquidity: Decimal | None


@dataclass(frozen=True)
class SimulateAprHourly:
    hour_ts: datetime
    fees_usd: Decimal
    volume_usd: Decimal | None


@dataclass(frozen=True)
class SimulateAprSnapshotHourly:
    hour_ts: datetime
    tick: int | None
    liquidity: Decimal | None


@dataclass(frozen=True)
class SimulateAprInitializedTick:
    tick_idx: int
    liquidity_net: Decimal
