from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class SimulateAprV2Request(BaseModel):
    pool_address: str = Field(..., description="Endereco da pool (0x...).")
    chain_id: int = Field(..., gt=0, description="Identificador numerico da chain.")
    dex_id: int = Field(..., gt=0, description="Identificador numerico da DEX.")
    deposit_usd: Decimal | None = Field(None, description="Valor total depositado em USD.")
    amount_token0: Decimal | None = Field(None, description="Quantidade de token0 na posicao.")
    amount_token1: Decimal | None = Field(None, description="Quantidade de token1 na posicao.")

    full_range: bool = Field(False, description="Quando true, simula a posicao Full Range (Uniswap V3).")

    tick_lower: int | None = Field(None, description="Tick inferior da faixa.")
    tick_upper: int | None = Field(None, description="Tick superior da faixa.")
    min_price: Decimal | None = Field(None, description="Preco minimo token1/token0.")
    max_price: Decimal | None = Field(None, description="Preco maximo token1/token0.")

    horizon: str = Field("7d", description="Horizonte dinamico (ex.: 24h, 7d, 14d, 30d).")
    lookback_days: int = Field(7, ge=1, description="Dias de lookback para escolher snapshots A e B.")
    calculation_method: str = Field(
        "current",
        description="Metodo de calculo: current|avg_liquidity_in_range|peak_liquidity_in_range|custom.",
    )
    custom_calculation_price: Decimal | None = Field(
        None,
        description="Preco customizado (obrigatorio quando calculation_method=custom).",
    )
    apr_method: Literal["exact"] = Field("exact", description="Metodo de APR; v2 suporta apenas exact.")
    swapped_pair: bool = Field(False, description="Quando true, interpreta/retorna dados no par invertido.")


class SimulateAprV2MetaResponse(BaseModel):
    block_a_number: int
    block_b_number: int
    ts_a: int
    ts_b: int
    seconds_delta: int
    used_price: Decimal
    warnings: list[str]


class SimulateAprV2Response(BaseModel):
    estimated_fees_period_usd: Decimal
    estimated_fees_24h_usd: Decimal
    monthly_usd: Decimal
    yearly_usd: Decimal
    fee_apr: Decimal
    meta: SimulateAprV2MetaResponse
