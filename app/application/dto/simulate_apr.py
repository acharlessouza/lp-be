from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SimulateAprInput:
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
    mode: str
    calculation_method: str
    custom_calculation_price: Decimal | None
    lookback_days: int


@dataclass(frozen=True)
class SimulateAprOutput:
    estimated_fees_24h_usd: Decimal
    monthly_usd: Decimal
    yearly_usd: Decimal
    fee_apr: Decimal
