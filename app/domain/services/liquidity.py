from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.simulate_apr import SimulateAprInitializedTick


@dataclass(frozen=True)
class LiquidityCurve:
    ticks: list[int]
    cumulative: list[Decimal]


def position_liquidity_v3(
    *,
    amount_token0: Decimal,
    amount_token1: Decimal,
    sqrt_price_current: Decimal,
    sqrt_price_lower: Decimal,
    sqrt_price_upper: Decimal,
    token0_decimals: int,
    token1_decimals: int,
) -> Decimal:
    if amount_token0 < 0 or amount_token1 < 0:
        return Decimal("0")
    if sqrt_price_current <= 0 or sqrt_price_lower <= 0 or sqrt_price_upper <= 0:
        return Decimal("0")
    if sqrt_price_lower >= sqrt_price_upper:
        return Decimal("0")

    amount0_raw = amount_token0 * (Decimal(10) ** Decimal(token0_decimals))
    amount1_raw = amount_token1 * (Decimal(10) ** Decimal(token1_decimals))
    sp = sqrt_price_current
    sa = sqrt_price_lower
    sb = sqrt_price_upper

    if sp <= sa:
        denom = sb - sa
        if denom <= 0:
            return Decimal("0")
        return amount0_raw * sa * sb / denom

    if sp >= sb:
        denom = sb - sa
        if denom <= 0:
            return Decimal("0")
        return amount1_raw / denom

    denom0 = sb - sp
    denom1 = sp - sa
    liquidity0 = Decimal("0")
    liquidity1 = Decimal("0")
    if denom0 > 0:
        liquidity0 = amount0_raw * sp * sb / denom0
    if denom1 > 0:
        liquidity1 = amount1_raw / denom1
    if liquidity0 > 0 and liquidity1 > 0:
        return min(liquidity0, liquidity1)
    return liquidity0 if liquidity0 > 0 else liquidity1


def build_liquidity_curve(initialized_ticks: list[SimulateAprInitializedTick]) -> LiquidityCurve:
    if not initialized_ticks:
        return LiquidityCurve(ticks=[], cumulative=[])

    ordered = sorted(initialized_ticks, key=lambda row: row.tick_idx)
    ticks: list[int] = []
    cumulative: list[Decimal] = []
    running = Decimal("0")
    for row in ordered:
        running += row.liquidity_net
        ticks.append(row.tick_idx)
        cumulative.append(running)
    return LiquidityCurve(ticks=ticks, cumulative=cumulative)


def active_liquidity_at_tick(*, curve: LiquidityCurve, tick: int) -> Decimal:
    if not curve.ticks:
        return Decimal("0")
    idx = bisect_right(curve.ticks, tick) - 1
    if idx < 0:
        return Decimal("0")
    value = curve.cumulative[idx]
    return value if value > 0 else Decimal("0")
