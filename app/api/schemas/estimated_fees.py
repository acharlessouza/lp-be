from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class EstimatedFeesRequest(BaseModel):
    pool_id: int = Field(..., description="Pool ID.")
    days: int = Field(..., ge=1, description="Calculation timeframe in days.")
    min_price: Decimal = Field(..., description="Min price (token1 per token0).")
    max_price: Decimal = Field(..., description="Max price (token1 per token0).")
    deposit_usd: Decimal = Field(..., description="Deposit amount in USD.")
    amount_token0: Decimal = Field(..., description="Token0 amount in the position.")
    amount_token1: Decimal = Field(..., description="Token1 amount in the position.")


class EstimatedFeesMonthlyResponse(BaseModel):
    value: Decimal
    percent: Decimal


class EstimatedFeesYearlyResponse(BaseModel):
    value: Decimal
    apr: Decimal


class EstimatedFeesResponse(BaseModel):
    estimated_fees_24h: Decimal
    monthly: EstimatedFeesMonthlyResponse
    yearly: EstimatedFeesYearlyResponse
