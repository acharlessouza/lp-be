from __future__ import annotations

from decimal import Decimal
from typing import Protocol


class TokenPricePort(Protocol):
    def get_pair_prices(
        self,
        *,
        token0_address: str,
        token1_address: str,
        network: str,
    ) -> tuple[Decimal, Decimal]:
        ...
