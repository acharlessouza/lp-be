from __future__ import annotations

from pydantic import BaseModel, Field


class PoolPriceStatsResponse(BaseModel):
    min: str | None = Field(None, description="Min token1_price in the timeframe.")
    max: str | None = Field(None, description="Max token1_price in the timeframe.")
    avg: str | None = Field(None, description="Avg token1_price in the timeframe.")
    price: str | None = Field(None, description="Current pool price (token1_price).")


class PoolPricePointResponse(BaseModel):
    timestamp: str
    price: str


class PoolPriceResponse(BaseModel):
    pool_id: int
    days: int
    stats: PoolPriceStatsResponse
    series: list[PoolPricePointResponse]
