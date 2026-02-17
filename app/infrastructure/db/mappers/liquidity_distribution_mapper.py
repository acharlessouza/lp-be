from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.liquidity_distribution import LiquidityDistributionPool, TickLiquidity


def map_row_to_liquidity_pool(row: Mapping[str, Any]) -> LiquidityDistributionPool:
    return LiquidityDistributionPool(
        id=row["id"],
        token0_symbol=row["token0_symbol"],
        token1_symbol=row["token1_symbol"],
        token0_decimals=row["token0_decimals"],
        token1_decimals=row["token1_decimals"],
        fee_tier=row["fee_tier"],
        tick_spacing=row["tick_spacing"],
        pool_tick=row["pool_tick"],
        current_tick=row["current_tick"],
        current_price_token1_per_token0=Decimal(str(row["current_price_token1_per_token0"]))
        if row["current_price_token1_per_token0"] is not None
        else None,
        onchain_liquidity=Decimal(str(row["onchain_liquidity"]))
        if row["onchain_liquidity"] is not None
        else None,
    )


def map_row_to_tick_liquidity(row: Mapping[str, Any]) -> TickLiquidity:
    return TickLiquidity(
        tick_idx=row["tick_idx"],
        liquidity_net=Decimal(str(row["liquidity_net"])),
    )
