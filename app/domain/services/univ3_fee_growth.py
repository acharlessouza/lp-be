from __future__ import annotations

from decimal import Decimal


Q128 = 2**128
UINT256_MOD = 2**256


def sub_uint256(a: int, b: int) -> int:
    return (a - b) % UINT256_MOD


def delta_uint256(new_value: int, old_value: int) -> int:
    return (new_value - old_value) % UINT256_MOD


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
        else sub_uint256(fee_growth_global, fee_growth_outside_lower)
    )
    fee_growth_above = (
        fee_growth_outside_upper
        if tick_current < tick_upper
        else sub_uint256(fee_growth_global, fee_growth_outside_upper)
    )
    return sub_uint256(
        sub_uint256(fee_growth_global, fee_growth_below),
        fee_growth_above,
    )


def fees_from_delta_inside(*, delta_inside: int, user_liquidity: Decimal) -> Decimal:
    if delta_inside < 0:
        raise ValueError("deltaInside must be non-negative.")
    if user_liquidity < 0:
        raise ValueError("user_liquidity must be non-negative.")
    return (user_liquidity * Decimal(delta_inside)) / Decimal(Q128)
