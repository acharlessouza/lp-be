from __future__ import annotations

import math
from decimal import Decimal
from typing import Literal


LOG_BASE = math.log(1.0001)


def tick_to_price(tick: int | float, token0_decimals: int, token1_decimals: int) -> float:
    decimal_adjust = 10 ** (token0_decimals - token1_decimals)
    return math.exp(float(tick) * LOG_BASE) * decimal_adjust


def price_to_tick_floor(price: float, token0_decimals: int, token1_decimals: int) -> int:
    return math.floor(_price_to_tick_value(price, token0_decimals, token1_decimals))


def price_to_tick_ceil(price: float, token0_decimals: int, token1_decimals: int) -> int:
    return math.ceil(_price_to_tick_value(price, token0_decimals, token1_decimals))


def align_tick_floor(tick: int, tick_spacing: int) -> int:
    if tick_spacing <= 0:
        raise ValueError("tick_spacing must be positive.")
    return math.floor(tick / tick_spacing) * tick_spacing


def align_tick_ceil(tick: int, tick_spacing: int) -> int:
    if tick_spacing <= 0:
        raise ValueError("tick_spacing must be positive.")
    return math.ceil(tick / tick_spacing) * tick_spacing


def calculate_preset_range(
    *,
    preset: Literal["stable", "wide"],
    current_tick: int,
    current_price: Decimal | float,
    tick_spacing: int,
    swapped_pair: bool,
    token0_decimals: int,
    token1_decimals: int,
) -> tuple[float, float, int, int]:
    if tick_spacing <= 0:
        raise ValueError("tick_spacing must be positive.")
    if current_price is None or float(current_price) <= 0:
        raise ValueError("current_price must be positive.")

    if preset == "stable":
        current_tick_aligned = align_tick_floor(current_tick, tick_spacing)
        min_tick = current_tick_aligned - (3 * tick_spacing)
        max_tick = current_tick_aligned + (3 * tick_spacing)
    elif preset == "wide":
        ref_price = float(current_price)
        if swapped_pair:
            ref_price = 1.0 / ref_price

        min_price_target = ref_price * 0.5
        max_price_target = ref_price * 2.0

        min_tick_raw = price_to_tick_floor(min_price_target, token0_decimals, token1_decimals)
        max_tick_raw = price_to_tick_ceil(max_price_target, token0_decimals, token1_decimals)
        min_tick = align_tick_floor(min_tick_raw, tick_spacing)
        max_tick = align_tick_ceil(max_tick_raw, tick_spacing)
    else:
        raise ValueError("preset must be one of: stable, wide.")

    if min_tick >= max_tick:
        max_tick = min_tick + tick_spacing

    min_price = tick_to_price(min_tick, token0_decimals, token1_decimals)
    max_price = tick_to_price(max_tick, token0_decimals, token1_decimals)
    if swapped_pair:
        min_price = 1.0 / min_price
        max_price = 1.0 / max_price

    min_price, max_price = _ordered_prices(min_price, max_price)
    return min_price, max_price, min_tick, max_tick


def _price_to_tick_value(price: float, token0_decimals: int, token1_decimals: int) -> float:
    if price < 0:
        raise ValueError("price must be positive.")

    decimal_adjust = 10 ** (token0_decimals - token1_decimals)
    raw_price = price / decimal_adjust
    if raw_price <= 0:
        raise ValueError("price produced invalid raw value.")
    return math.log(raw_price) / LOG_BASE


def _ordered_prices(a: float, b: float) -> tuple[float, float]:
    if a <= b:
        return a, b
    return b, a
