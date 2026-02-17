from __future__ import annotations

from typing import Protocol

from app.domain.entities.simulate_apr import (
    SimulateAprHourly,
    SimulateAprInitializedTick,
    SimulateAprPool,
    SimulateAprPoolState,
    SimulateAprSnapshotHourly,
)


class SimulateAprPort(Protocol):
    def get_pool(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPool | None:
        ...

    def get_latest_pool_state(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPoolState | None:
        ...

    def get_pool_hourly(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        hours: int,
    ) -> list[SimulateAprHourly]:
        ...

    def get_pool_state_snapshots_hourly(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        hours: int,
    ) -> list[SimulateAprSnapshotHourly]:
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
