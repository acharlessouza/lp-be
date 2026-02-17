from __future__ import annotations

import math
from decimal import Decimal


LOG_BASE = math.log(1.0001)
Q96 = Decimal(2) ** 96


def tick_to_price(tick: int | float, token0_decimals: int, token1_decimals: int) -> Decimal:
    decimal_adjust = 10 ** (token0_decimals - token1_decimals)
    value = math.exp(float(tick) * LOG_BASE) * decimal_adjust
    return Decimal(str(value))


def price_to_tick_floor(price: Decimal, token0_decimals: int, token1_decimals: int) -> int:
    return math.floor(_price_to_tick_value(price, token0_decimals, token1_decimals))


def price_to_tick_ceil(price: Decimal, token0_decimals: int, token1_decimals: int) -> int:
    return math.ceil(_price_to_tick_value(price, token0_decimals, token1_decimals))


def tick_to_sqrt_price(tick: int | float) -> Decimal:
    return Decimal(str(math.exp(float(tick) * LOG_BASE / 2.0)))


def tick_to_sqrt_price_x96(tick: int | float) -> int:
    sqrt_price = tick_to_sqrt_price(tick)
    return int((sqrt_price * Q96).to_integral_value())


def sqrt_price_x96_to_sqrt_price(sqrt_price_x96: int) -> Decimal:
    if sqrt_price_x96 <= 0:
        raise ValueError("Invalid sqrt_price_x96.")
    return Decimal(sqrt_price_x96) / Q96


def sqrt_price_x96_to_price(
    sqrt_price_x96: int,
    token0_decimals: int,
    token1_decimals: int,
) -> Decimal:
    sqrt_price = sqrt_price_x96_to_sqrt_price(sqrt_price_x96)
    raw_price = sqrt_price * sqrt_price
    decimal_adjust = Decimal(10) ** Decimal(token0_decimals - token1_decimals)
    return raw_price * decimal_adjust


def _price_to_tick_value(price: Decimal, token0_decimals: int, token1_decimals: int) -> float:
    if price < 0:
        raise ValueError("price must be positive.")
    decimal_adjust = Decimal(10) ** Decimal(token0_decimals - token1_decimals)
    raw_price = price / decimal_adjust
    if raw_price <= 0:
        raise ValueError("price produced invalid raw value.")
    return math.log(float(raw_price)) / LOG_BASE
