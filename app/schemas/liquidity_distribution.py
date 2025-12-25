from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LiquidityDistributionRequest(BaseModel):
    pool_id: int = Field(..., description="Pool ID.")
    snapshot_date: date = Field(..., description="Snapshot date (YYYY-MM-DD).")
    current_tick: int = Field(
        ...,
        description="Legacy field (ignored, computed from DB unless center_tick is set).",
    )
    center_tick: int | None = Field(
        None,
        description="Center tick for pan (when provided, subgraph lookup is skipped).",
    )
    tick_range: int = Field(..., ge=1, description="Tick range (ex: 6000).")
    range_min: Decimal | None = Field(None, description="Min price range (token1 per token0).")
    range_max: Decimal | None = Field(None, description="Max price range (token1 per token0).")


class LiquidityDistributionPool(BaseModel):
    token0: str
    token1: str


class LiquidityDistributionPoint(BaseModel):
    tick: int
    liquidity: str
    price: float


class LiquidityDistributionResponse(BaseModel):
    pool: LiquidityDistributionPool
    current_tick: int
    data: list[LiquidityDistributionPoint]
