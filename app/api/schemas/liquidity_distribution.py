from __future__ import annotations

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field


class LiquidityDistributionRequest(BaseModel):
    pool_id: int | str = Field(..., description="Pool ID numerico legado ou pool_address (0x...).")
    chain_id: int | None = Field(None, description="Opcional para desambiguar pool_address.")
    dex_id: int | None = Field(None, description="Opcional para desambiguar pool_address.")
    snapshot_date: date = Field(..., description="Snapshot date (YYYY-MM-DD).")
    current_tick: int = Field(
        ...,
        description="Legacy field (ignored, computed from DB unless center_tick is set).",
    )
    center_tick: int | None = Field(
        None,
        description="Center tick for pan (when provided, DB lookup is skipped).",
    )
    tick_range: int = Field(..., ge=1, description="Tick range (ex: 6000).")
    range_min: Decimal | None = Field(None, description="Min price range (token1 per token0).")
    range_max: Decimal | None = Field(None, description="Max price range (token1 per token0).")
    swapped_pair: bool = Field(
        False,
        description="Quando true, interpreta entrada e retorna saida no par invertido.",
    )


class LiquidityDistributionPoolResponse(BaseModel):
    token0: str
    token1: str


class LiquidityDistributionPointResponse(BaseModel):
    tick: int
    liquidity: str
    price: float


class LiquidityDistributionResponse(BaseModel):
    pool: LiquidityDistributionPoolResponse
    current_tick: int
    data: list[LiquidityDistributionPointResponse]


class LiquidityDistributionDefaultRangeRequest(BaseModel):
    pool_id: int | str = Field(..., description="Pool ID numerico legado ou pool_address (0x...).")
    chain_id: int | None = Field(None, description="Opcional para desambiguar pool_address.")
    dex_id: int | None = Field(None, description="Opcional para desambiguar pool_address.")
    snapshot_date: date = Field(..., description="Snapshot date (YYYY-MM-DD).")
    preset: str = Field(
        "stable",
        description="Preset da Uniswap para range default (stable ou wide).",
    )
    initial_price: Decimal | float | None = Field(
        None,
        gt=0,
        description="Preco inicial token1 por token0. Quando ausente, o backend deriva do estado atual da pool.",
    )
    center_tick: int | None = Field(
        None,
        description="Tick central opcional. Quando informado, substitui o tick atual da pool.",
    )
    swapped_pair: bool = Field(
        False,
        description="Quando true, calcula e retorna precos no par invertido (1/price).",
    )


class LiquidityDistributionDefaultRangeResponse(BaseModel):
    min_price: float
    max_price: float
    min_tick: int
    max_tick: int
    tick_spacing: int
