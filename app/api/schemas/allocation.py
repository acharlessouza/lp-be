from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class AllocationRequest(BaseModel):
    pool_address: str = Field(..., description="Pool address from the pools table.")
    rede: str = Field(..., description="Network name (e.g. arbitrum).")
    amount: Decimal = Field(..., description="Deposit amount in USD.")
    range1: Decimal = Field(..., description="Min range value (token1/token0).")
    range2: Decimal = Field(..., description="Max range value (token1/token0).")


class AllocationResponse(BaseModel):
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
