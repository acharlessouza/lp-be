from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class SimulateAprRequest(BaseModel):
    pool_address: str = Field(..., description="Endereco da pool (0x...).")
    chain_id: int = Field(..., description="Identificador numerico da chain.")
    dex_id: int = Field(..., description="Identificador numerico da DEX.")
    deposit_usd: Decimal | None = Field(None, description="Valor total depositado em USD.")
    amount_token0: Decimal | None = Field(None, description="Quantidade de token0 na posicao.")
    amount_token1: Decimal | None = Field(None, description="Quantidade de token1 na posicao.")
    tick_lower: int | None = Field(None, description="Tick inferior da faixa.")
    tick_upper: int | None = Field(None, description="Tick superior da faixa.")
    min_price: Decimal | None = Field(None, description="Preco minimo token1/token0.")
    max_price: Decimal | None = Field(None, description="Preco maximo token1/token0.")
    horizon: str = Field("7d", description="Horizonte dinamico (ex.: 24h, 7d, 14d, 30d).")
    mode: str = Field("A", description="Modo de simulacao: A (tick constante) ou B (tick path).")
    lookback_days: int = Field(7, ge=1, description="Dias de historico para leitura de horas.")


class SimulateAprDiagnosticsResponse(BaseModel):
    hours_total: int
    hours_in_range: int
    percent_time_in_range: Decimal
    avg_share_in_range: Decimal
    assumptions: dict[str, str]
    warnings: list[str]


class SimulateAprResponse(BaseModel):
    estimated_fees_24h_usd: Decimal
    monthly_usd: Decimal
    yearly_usd: Decimal
    fee_apr: Decimal
    diagnostics: SimulateAprDiagnosticsResponse
