from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from app.domain.entities.estimated_fees import EstimatedFeesAggregates, EstimatedFeesPool
from app.domain.entities.pool_price import PoolCurrentPrice


class EstimatedFeesPort(Protocol):
    def get_pool_by_id(self, *, pool_id: int) -> EstimatedFeesPool | None:
        ...

    def get_aggregates(
        self,
        *,
        pool_id: int,
        days: int,
        min_price: Decimal,
        max_price: Decimal,
    ) -> EstimatedFeesAggregates:
        ...

    def get_latest_price(self, *, pool_id: int) -> PoolCurrentPrice | None:
        ...
