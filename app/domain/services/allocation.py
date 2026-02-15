from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext

from app.domain.exceptions import AllocationInputError


@dataclass(frozen=True)
class AllocationAmounts:
    amount_token0: Decimal
    amount_token1: Decimal


def split_deposit_range(
    *,
    deposit_usd: Decimal,
    price_token0_usd: Decimal,
    price_token1_usd: Decimal,
    range_min: Decimal,
    range_max: Decimal,
) -> AllocationAmounts:
    if price_token0_usd <= 0 or price_token1_usd <= 0:
        raise AllocationInputError("Token prices must be positive.")
    if range_min <= 0 or range_max <= 0:
        raise AllocationInputError("Ranges must be positive.")
    if range_min >= range_max:
        raise AllocationInputError("range1 must be lower than range2.")

    price_current = price_token0_usd / price_token1_usd
    ctx = getcontext()
    sa = range_min.sqrt(ctx)
    sb = range_max.sqrt(ctx)
    sp = price_current.sqrt(ctx)

    if sp <= sa:
        return AllocationAmounts(
            amount_token0=deposit_usd / price_token0_usd,
            amount_token1=Decimal("0"),
        )
    if sp >= sb:
        return AllocationAmounts(
            amount_token0=Decimal("0"),
            amount_token1=deposit_usd / price_token1_usd,
        )

    amount0_per_l = (Decimal("1") / sp) - (Decimal("1") / sb)
    amount1_per_l = sp - sa
    value_per_l = amount0_per_l * price_token0_usd + amount1_per_l * price_token1_usd
    liquidity = deposit_usd / value_per_l
    amount0 = liquidity * amount0_per_l
    amount1 = liquidity * amount1_per_l
    return AllocationAmounts(amount_token0=amount0, amount_token1=amount1)
