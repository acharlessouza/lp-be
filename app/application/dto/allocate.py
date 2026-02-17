from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AllocateInput:
    pool_address: str
    chain_id: int
    dex_id: int
    deposit_usd: Decimal
    range_min: Decimal
    range_max: Decimal


@dataclass(frozen=True)
class AllocateOutput:
    pool_address: str
    rede: str
    taxa: int
    token0_address: str
    token0_symbol: str
    token1_address: str
    token1_symbol: str
    amount_token0: Decimal
    amount_token1: Decimal
    price_token0_usd: Decimal
    price_token1_usd: Decimal
