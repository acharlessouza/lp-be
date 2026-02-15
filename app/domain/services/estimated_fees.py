from __future__ import annotations

from decimal import Decimal, getcontext

from app.domain.entities.estimated_fees import EstimatedFeesBreakdown


def position_liquidity(
    *,
    amount_token0: Decimal,
    amount_token1: Decimal,
    price_current: Decimal,
    price_min: Decimal,
    price_max: Decimal,
    token0_decimals: int,
    token1_decimals: int,
) -> Decimal:
    if price_current <= 0 or price_min <= 0 or price_max <= 0:
        return Decimal("0")
    if price_min >= price_max:
        return Decimal("0")

    decimal_delta = token1_decimals - token0_decimals
    decimal_adjust = Decimal("10") ** Decimal(decimal_delta)
    price_current_raw = price_current * decimal_adjust
    price_min_raw = price_min * decimal_adjust
    price_max_raw = price_max * decimal_adjust
    amount0_raw = amount_token0 * (Decimal("10") ** Decimal(token0_decimals))
    amount1_raw = amount_token1 * (Decimal("10") ** Decimal(token1_decimals))

    ctx = getcontext()
    sa = price_min_raw.sqrt(ctx)
    sb = price_max_raw.sqrt(ctx)
    sp = price_current_raw.sqrt(ctx)

    if sp <= sa:
        denom = (Decimal("1") / sa) - (Decimal("1") / sb)
        return amount0_raw / denom if denom > 0 else Decimal("0")
    if sp >= sb:
        denom = sb - sa
        return amount1_raw / denom if denom > 0 else Decimal("0")

    amount0_per_l = (Decimal("1") / sp) - (Decimal("1") / sb)
    amount1_per_l = sp - sa
    liquidity0 = amount0_raw / amount0_per_l if amount0_per_l > 0 else Decimal("0")
    liquidity1 = amount1_raw / amount1_per_l if amount1_per_l > 0 else Decimal("0")
    if liquidity0 > 0 and liquidity1 > 0:
        return min(liquidity0, liquidity1)
    return liquidity0 if liquidity0 > 0 else liquidity1


def estimate_fees(
    *,
    pool_fees: Decimal,
    avg_liquidity: Decimal,
    in_range_days: Decimal,
    deposit_usd: Decimal,
    user_liquidity: Decimal,
) -> EstimatedFeesBreakdown:
    if (
        deposit_usd <= 0
        or avg_liquidity <= 0
        or pool_fees <= 0
        or in_range_days <= 0
        or user_liquidity <= 0
    ):
        return EstimatedFeesBreakdown(
            estimated_fees_24h=Decimal("0"),
            monthly_value=Decimal("0"),
            monthly_percent=Decimal("0"),
            yearly_value=Decimal("0"),
            yearly_apr=Decimal("0"),
        )

    share = user_liquidity / avg_liquidity
    estimated_period = pool_fees * share
    estimated_24h = estimated_period / in_range_days
    monthly_value = estimated_24h * Decimal("30")
    yearly_value = estimated_24h * Decimal("365")
    monthly_percent = (monthly_value / deposit_usd) * Decimal("100")
    yearly_apr = yearly_value / deposit_usd

    return EstimatedFeesBreakdown(
        estimated_fees_24h=estimated_24h,
        monthly_value=monthly_value,
        monthly_percent=monthly_percent,
        yearly_value=yearly_value,
        yearly_apr=yearly_apr,
    )
