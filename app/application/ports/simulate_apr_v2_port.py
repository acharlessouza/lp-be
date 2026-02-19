from __future__ import annotations

from typing import Protocol

from app.domain.entities.simulate_apr import SimulateAprInitializedTick
from app.domain.entities.simulate_apr_v2 import (
    SimulateAprV2Pool,
    SimulateAprV2PoolSnapshot,
    SimulateAprV2TickSnapshot,
)


class SimulateAprV2Port(Protocol):
    def get_pool(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprV2Pool | None:
        ...

    def get_latest_pool_snapshot(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprV2PoolSnapshot | None:
        ...

    def get_lookback_pool_snapshot(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        target_timestamp: int,
    ) -> SimulateAprV2PoolSnapshot | None:
        ...

    def get_tick_snapshots_for_blocks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> list[SimulateAprV2TickSnapshot]:
        ...

    def get_initialized_ticks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        min_tick: int,
        max_tick: int,
    ) -> list[SimulateAprInitializedTick]:
        ...
