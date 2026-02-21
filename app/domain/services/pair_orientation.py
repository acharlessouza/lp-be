from __future__ import annotations

from decimal import Decimal


def invert_decimal_price(price: Decimal, *, field_name: str = "price") -> Decimal:
    if price <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return Decimal("1") / price


def invert_float_price(price: float, *, field_name: str = "price") -> float:
    if price <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return 1.0 / price


def ui_price_range_to_canonical(
    min_price_ui: Decimal,
    max_price_ui: Decimal,
    *,
    min_field_name: str = "min_price",
    max_field_name: str = "max_price",
) -> tuple[Decimal, Decimal]:
    if min_price_ui <= 0 or max_price_ui <= 0:
        raise ValueError(f"{min_field_name} and {max_field_name} must be positive.")
    if min_price_ui >= max_price_ui:
        raise ValueError(f"{min_field_name} must be lower than {max_field_name}.")
    return invert_decimal_price(max_price_ui, field_name=max_field_name), invert_decimal_price(
        min_price_ui,
        field_name=min_field_name,
    )


def canonical_price_range_to_ui(
    min_price_canonical: Decimal,
    max_price_canonical: Decimal,
    *,
    min_field_name: str = "min_price",
    max_field_name: str = "max_price",
) -> tuple[Decimal, Decimal]:
    if min_price_canonical <= 0 or max_price_canonical <= 0:
        raise ValueError(f"{min_field_name} and {max_field_name} must be positive.")
    if min_price_canonical >= max_price_canonical:
        raise ValueError(f"{min_field_name} must be lower than {max_field_name}.")
    return invert_decimal_price(
        max_price_canonical,
        field_name=max_field_name,
    ), invert_decimal_price(min_price_canonical, field_name=min_field_name)


def ui_ticks_to_canonical(tick_lower_ui: int, tick_upper_ui: int) -> tuple[int, int]:
    tick_lower_canonical = -tick_upper_ui
    tick_upper_canonical = -tick_lower_ui
    if tick_lower_canonical >= tick_upper_canonical:
        raise ValueError("tick_lower must be lower than tick_upper.")
    return tick_lower_canonical, tick_upper_canonical


def canonical_ticks_to_ui(tick_lower_canonical: int, tick_upper_canonical: int) -> tuple[int, int]:
    tick_lower_ui = -tick_upper_canonical
    tick_upper_ui = -tick_lower_canonical
    if tick_lower_ui >= tick_upper_ui:
        raise ValueError("tick_lower must be lower than tick_upper.")
    return tick_lower_ui, tick_upper_ui


def swap_optional_amounts(
    amount_token0: Decimal | None,
    amount_token1: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    return amount_token1, amount_token0
