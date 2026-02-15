from __future__ import annotations

import math
from decimal import Decimal

from app.domain.entities.liquidity_distribution import TickLiquidity


def build_liquidity_distribution(
    *,
    rows: list[TickLiquidity],
    current_tick: int,
    min_tick: int,
    max_tick: int,
    onchain_liquidity: Decimal,
    token0_decimals: int,
    token1_decimals: int,
) -> list[tuple[int, Decimal, float]]:
    decimal_adjust = 10 ** (token0_decimals - token1_decimals)
    log_base = math.log(1.0001)

    cumulative = Decimal("0")
    cumulative_at_current = Decimal("0")
    for row in rows:
        cumulative += row.liquidity_net
        if row.tick_idx <= current_tick:
            cumulative_at_current = cumulative

    baseline = onchain_liquidity - cumulative_at_current

    points: list[tuple[int, Decimal, float]] = []
    cumulative = Decimal("0")
    for row in rows:
        cumulative += row.liquidity_net
        if min_tick <= row.tick_idx <= max_tick:
            points.append(
                (
                    row.tick_idx,
                    baseline + cumulative,
                    math.exp(row.tick_idx * log_base) * decimal_adjust,
                )
            )

    return points
