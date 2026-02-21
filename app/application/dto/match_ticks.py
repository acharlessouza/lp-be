from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class MatchTicksInput:
    pool_id: int
    min_price: Decimal
    max_price: Decimal
    swapped_pair: bool = False


@dataclass(frozen=True)
class MatchTicksOutput:
    min_price_matched: float
    max_price_matched: float
    current_price_matched: float
