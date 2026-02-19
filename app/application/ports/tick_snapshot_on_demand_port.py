from __future__ import annotations

from typing import Protocol

from app.application.dto.tick_snapshot_on_demand import (
    BlockUpsertRow,
    MissingTickSnapshot,
    TickSnapshotUpsertRow,
)


class TickSnapshotOnDemandPort(Protocol):
    def get_missing_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> list[MissingTickSnapshot]:
        ...

    def fetch_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        combinations: list[MissingTickSnapshot],
    ) -> list[TickSnapshotUpsertRow]:
        ...

    def upsert_tick_snapshots(self, *, rows: list[TickSnapshotUpsertRow]) -> int:
        ...

    def fetch_blocks_metadata(
        self,
        *,
        chain_id: int,
        block_numbers: list[int],
    ) -> list[BlockUpsertRow]:
        ...

    def upsert_blocks(self, *, rows: list[BlockUpsertRow]) -> int:
        ...
