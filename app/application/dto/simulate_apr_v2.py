from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SimulateAprV2Input:
    pool_address: str
    chain_id: int
    dex_id: int
    deposit_usd: Decimal | None
    amount_token0: Decimal | None
    amount_token1: Decimal | None
    full_range: bool
    tick_lower: int | None
    tick_upper: int | None
    min_price: Decimal | None
    max_price: Decimal | None
    horizon: str
    lookback_days: int
    calculation_method: str
    custom_calculation_price: Decimal | None
    apr_method: str
    swapped_pair: bool = False


@dataclass(frozen=True)
class SimulateAprV2MetaOutput:
    block_a_number: int
    block_b_number: int
    ts_a: int
    ts_b: int
    seconds_delta: int
    used_price: Decimal
    warnings: list[str]


@dataclass(frozen=True)
class SimulateAprV2Output:
    estimated_fees_period_usd: Decimal
    estimated_fees_24h_usd: Decimal
    monthly_usd: Decimal
    yearly_usd: Decimal
    fee_apr: Decimal
    meta: SimulateAprV2MetaOutput
