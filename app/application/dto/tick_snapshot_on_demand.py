from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MissingTickSnapshot:
    block_number: int
    tick_idx: int


@dataclass(frozen=True)
class TickSnapshotUpsertRow:
    dex_id: int
    chain_id: int
    pool_address: str
    block_number: int
    tick_idx: int
    fee_growth_outside0_x128: str | int | None
    fee_growth_outside1_x128: str | int | None
    liquidity_gross: str | int | None = None
    liquidity_net: str | int | None = None


@dataclass(frozen=True)
class BlockUpsertRow:
    chain_id: int
    block_number: int
    timestamp: int


@dataclass(frozen=True)
class InitializedTickSourceRow:
    tick_idx: int
    liquidity_net: str | int | None
    liquidity_gross: str | int | None = None
    price0: str | int | None = None
    price1: str | int | None = None
    fee_growth_outside0_x128: str | int | None = None
    fee_growth_outside1_x128: str | int | None = None
    updated_at_block: int | None = None
