from __future__ import annotations

from typing import Protocol


class PoolRuntimeMetadataPort(Protocol):
    def upsert_pool_activity(
        self,
        *,
        chain_id: int,
        dex_id: int,
        pool_address: str,
    ) -> None:
        ...

    def upsert_pool_ticks_window_refresh_state(
        self,
        *,
        chain_id: int,
        dex_id: int,
        pool_address: str,
        window_ticks: int,
        center_tick: int | None,
        last_pool_tick: int | None,
        last_block_number: int | None = None,
        source: str = "simulate_apr_v2",
    ) -> None:
        ...
