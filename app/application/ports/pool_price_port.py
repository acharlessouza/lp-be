from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities.pool_price import PoolCurrentPrice, PoolPricePoint, PoolPriceStats


class PoolPricePort(Protocol):
    def pool_exists(self, *, pool_address: str, chain_id: int, dex_id: int) -> bool:
        ...

    def get_series(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        days: int,
    ) -> list[PoolPricePoint]:
        ...

    def get_series_range(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        start: datetime,
        end: datetime,
    ) -> list[PoolPricePoint]:
        ...

    def get_stats(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        days: int,
    ) -> PoolPriceStats:
        ...

    def get_stats_range(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        start: datetime,
        end: datetime,
    ) -> PoolPriceStats:
        ...

    def get_latest_price(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> PoolCurrentPrice | None:
        ...
