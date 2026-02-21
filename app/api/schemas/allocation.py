from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class AllocationRequest(BaseModel):
    pool_address: str = Field(..., description="Pool address from the pools table.")
    chain_id: int = Field(..., gt=0, description="Chain ID da pool.")
    dex_id: int = Field(..., gt=0, description="Dex ID da pool.")
    amount: Decimal = Field(..., description="Deposit amount in USD.")
    full_range: bool = Field(False, description="Quando true, faz alocacao Full Range com split 50/50 em valor USD.")
    range1: Decimal | None = Field(None, description="Min range value (token1/token0). Obrigatorio quando full_range=false.")
    range2: Decimal | None = Field(None, description="Max range value (token1/token0). Obrigatorio quando full_range=false.")
    swapped_pair: bool = Field(False, description="Quando true, interpreta a faixa no par invertido.")


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
