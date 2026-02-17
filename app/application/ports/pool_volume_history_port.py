from __future__ import annotations

from typing import Protocol

from app.domain.entities.pool_volume_history import (
    PoolVolumeHistoryPoint,
    PoolVolumeHistorySummaryBase,
    PoolVolumeHistorySummaryPremium,
)


class PoolVolumeHistoryPort(Protocol):
    def list_daily_volume_history(
        self,
        *,
        pool_address: str,
        days: int,
        chain_id: int | None,
        dex_id: int | None,
    ) -> list[PoolVolumeHistoryPoint]:
        ...

    def get_summary_base(
        self,
        *,
        pool_address: str,
        days: int,
        chain_id: int | None,
        dex_id: int | None,
    ) -> PoolVolumeHistorySummaryBase:
        ...

    def get_summary_premium(
        self,
        *,
        exchange: str,
        symbol0: str,
        symbol1: str | None,
        days: int,
    ) -> PoolVolumeHistorySummaryPremium:
        ...
