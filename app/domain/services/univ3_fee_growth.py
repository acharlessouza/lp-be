from __future__ import annotations

from decimal import Decimal


Q128 = 2**128


def parse_uint256(value: int | str | Decimal | None) -> int:
    if value is None:
        raise ValueError("Missing uint256 value.")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("Empty uint256 string.")
        parsed = int(raw)
    elif isinstance(value, Decimal):
        if value != value.to_integral_value():
            raise ValueError("Decimal uint256 value must be integral.")
        parsed = int(value)
    else:
        raise ValueError("Unsupported uint256 value type.")

    if parsed < 0:
        raise ValueError("uint256 value must be non-negative.")
    return parsed


def fee_growth_inside(
    *,
    fee_growth_global: int,
    fee_growth_outside_lower: int,
    fee_growth_outside_upper: int,
    tick_current: int,
    tick_lower: int,
    tick_upper: int,
) -> int:
    fee_growth_below = (
        fee_growth_outside_lower
        if tick_current >= tick_lower
        else fee_growth_global - fee_growth_outside_lower
    )
    fee_growth_above = (
        fee_growth_outside_upper
        if tick_current < tick_upper
        else fee_growth_global - fee_growth_outside_upper
    )
    inside = fee_growth_global - fee_growth_below - fee_growth_above
    if inside < 0:
        raise ValueError("feeGrowthInside is negative.")
    return inside


def fees_from_delta_inside(*, delta_inside: int, user_liquidity: Decimal) -> Decimal:
    if delta_inside < 0:
        raise ValueError("deltaInside must be non-negative.")
    if user_liquidity < 0:
        raise ValueError("user_liquidity must be non-negative.")
    return (user_liquidity * Decimal(delta_inside)) / Decimal(Q128)
