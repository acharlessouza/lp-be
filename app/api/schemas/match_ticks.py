from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class MatchTicksRequest(BaseModel):
    pool_id: int = Field(..., description="Pool ID.")
    min_price: Decimal = Field(..., description="Min price (token1 per token0).")
    max_price: Decimal = Field(..., description="Max price (token1 per token0).")
    swapped_pair: bool = Field(False, description="Quando true, interpreta o range no par invertido.")


class MatchTicksResponse(BaseModel):
    min_price_matched: float
    max_price_matched: float
    current_price_matched: float
