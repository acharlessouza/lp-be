from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities.liquidity_distribution import LiquidityDistributionPool, TickLiquidity


class LiquidityDistributionPort(Protocol):
    def get_pool_by_id(self, *, pool_id: int) -> LiquidityDistributionPool | None:
        ...

    def find_pools_by_address(
        self,
        *,
        pool_address: str,
        chain_id: int | None = None,
        dex_id: int | None = None,
    ) -> list[LiquidityDistributionPool]:
        ...

    def get_latest_period_start(self, *, pool_id: int) -> datetime | None:
        ...

    def get_ticks_by_period(self, *, pool_id: int, period_start: datetime) -> list[TickLiquidity]:
        ...
