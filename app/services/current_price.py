from __future__ import annotations

from decimal import Decimal, getcontext


getcontext().prec = 50

Q96 = Decimal(2) ** 96


def price_from_sqrt_price_x96(sqrt_price_x96: int) -> Decimal:
    if sqrt_price_x96 <= 0:
        raise ValueError("Invalid sqrt_price_x96.")
    sqrt_price = Decimal(sqrt_price_x96) / Q96
    return sqrt_price**2


def resolve_current_price(
    *,
    token1_price: Decimal | None,
    token0_price: Decimal | None,
    sqrt_price_x96: int | None,
) -> Decimal:
    if token1_price is not None:
        if token1_price <= 0:
            raise ValueError("Invalid pool price.")
        return token1_price
    if token0_price is not None:
        if token0_price <= 0:
            raise ValueError("Invalid pool price.")
        return Decimal("1") / token0_price
    if sqrt_price_x96 is None:
        raise ValueError("Pool price not found in database.")
    price = price_from_sqrt_price_x96(sqrt_price_x96)
    if price <= 0:
        raise ValueError("Invalid pool price.")
    return price
