from __future__ import annotations

from pydantic import BaseModel


class ExchangeResponse(BaseModel):
    id: int
    name: str
    icon_url: str | None = None


class NetworkResponse(BaseModel):
    id: int
    name: str
    icon_url: str | None = None


class TokenResponse(BaseModel):
    address: str
    symbol: str
    decimals: int
    icon_url: str | None = None


class PoolSummaryResponse(BaseModel):
    pool_address: str
    fee_tier: int


class PoolDetailResponse(BaseModel):
    id: str
    dex_key: str
    dex_name: str
    dex_version: str | None
    chain_key: str
    chain_name: str
    fee_tier: int
    token0_address: str
    token0_symbol: str
    token0_decimals: int
    token1_address: str
    token1_symbol: str
    token1_decimals: int
