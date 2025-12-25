from __future__ import annotations

from pydantic import BaseModel


class PoolDetailResponse(BaseModel):
    id: int
    fee_tier: int
    token0_address: str
    token0_symbol: str
    token0_decimals: int
    token1_address: str
    token1_symbol: str
    token1_decimals: int
