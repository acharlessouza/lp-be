from __future__ import annotations

import math
from decimal import Decimal, getcontext


getcontext().prec = 50

Q96 = Decimal(2) ** 96


def tick_from_sqrt_price_x96(sqrt_price_x96: int) -> int:
    if sqrt_price_x96 <= 0:
        raise ValueError("Invalid sqrt_price_x96.")
    sqrt_price = Decimal(sqrt_price_x96) / Q96
    price = sqrt_price**2
    tick = math.floor(math.log(float(price)) / math.log(1.0001))
    return tick
