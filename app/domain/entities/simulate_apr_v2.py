from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SimulateAprV2Pool:
    dex_id: int
    chain_id: int
    pool_address: str
    token0_decimals: int
    token1_decimals: int
    fee_tier: int | None
    tick_spacing: int | None


@dataclass(frozen=True)
class SimulateAprV2PoolSnapshot:
    block_number: int
    block_timestamp: int
    tick: int | None
    sqrt_price_x96: int | None
    liquidity: Decimal | None
    fee_growth_global0_x128: int | str | None
    fee_growth_global1_x128: int | str | None


@dataclass(frozen=True)
class SimulateAprV2TickSnapshot:
    block_number: int
    tick_idx: int
    fee_growth_outside0_x128: int | str | None
    fee_growth_outside1_x128: int | str | None
    liquidity_net: Decimal | None
    liquidity_gross: Decimal | None
