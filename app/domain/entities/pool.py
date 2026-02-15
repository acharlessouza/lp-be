from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pool:
    network: str
    pool_address: str
    fee_tier: int
    token0_address: str
    token0_symbol: str
    token1_address: str
    token1_symbol: str
