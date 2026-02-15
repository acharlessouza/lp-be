from __future__ import annotations

import math


TICK_SPACING = {
    100: 1,
    500: 10,
    3000: 60,
    10000: 200,
}


def price_to_tick(price: float) -> float:
    return math.log(price) / math.log(1.0001)


def tick_to_price(tick: int) -> float:
    return 1.0001**tick


def match_tick(tick: float, spacing: int, mode: str) -> int:
    if mode == "lower":
        return math.floor(tick / spacing) * spacing
    if mode == "upper":
        return math.ceil(tick / spacing) * spacing
    if mode == "current":
        return round(tick / spacing) * spacing
    raise ValueError("Invalid match mode.")


def match_prices(
    *,
    min_price: float,
    max_price: float,
    current_price: float,
    fee_tier: int,
) -> tuple[float, float, float]:
    spacing = TICK_SPACING.get(fee_tier)
    if spacing is None:
        raise ValueError("Unsupported fee tier.")

    tick_min = price_to_tick(min_price)
    tick_max = price_to_tick(max_price)
    tick_current = price_to_tick(current_price)

    tick_min_matched = match_tick(tick_min, spacing, "lower")
    tick_max_matched = match_tick(tick_max, spacing, "upper")
    tick_current_matched = match_tick(tick_current, spacing, "current")

    return (
        tick_to_price(tick_min_matched),
        tick_to_price(tick_max_matched),
        tick_to_price(tick_current_matched),
    )
