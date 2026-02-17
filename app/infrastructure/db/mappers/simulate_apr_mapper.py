from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.simulate_apr import (
    SimulateAprHourly,
    SimulateAprInitializedTick,
    SimulateAprPool,
    SimulateAprPoolState,
    SimulateAprSnapshotHourly,
)


def map_row_to_simulate_apr_pool(row: Mapping[str, Any]) -> SimulateAprPool:
    return SimulateAprPool(
        dex_id=int(row["dex_id"]),
        chain_id=int(row["chain_id"]),
        pool_address=str(row["pool_address"]).lower(),
        token0_decimals=int(row["token0_decimals"] or 0),
        token1_decimals=int(row["token1_decimals"] or 0),
        fee_tier=int(row["fee_tier"]) if row["fee_tier"] is not None else None,
        tick_spacing=int(row["tick_spacing"]) if row["tick_spacing"] is not None else None,
    )


def map_row_to_simulate_apr_pool_state(row: Mapping[str, Any]) -> SimulateAprPoolState:
    return SimulateAprPoolState(
        tick=int(row["tick"]) if row["tick"] is not None else None,
        sqrt_price_x96=int(row["sqrt_price_x96"]) if row["sqrt_price_x96"] is not None else None,
        liquidity=Decimal(str(row["liquidity"])) if row["liquidity"] is not None else None,
    )


def map_row_to_simulate_apr_hourly(row: Mapping[str, Any]) -> SimulateAprHourly:
    return SimulateAprHourly(
        hour_ts=row["hour_ts"],
        fees_usd=Decimal(str(row["fees_usd"])) if row["fees_usd"] is not None else Decimal("0"),
        volume_usd=Decimal(str(row["volume_usd"])) if row["volume_usd"] is not None else None,
    )


def map_row_to_simulate_apr_snapshot_hourly(row: Mapping[str, Any]) -> SimulateAprSnapshotHourly:
    return SimulateAprSnapshotHourly(
        hour_ts=row["hour_ts"],
        tick=int(row["tick"]) if row["tick"] is not None else None,
        liquidity=Decimal(str(row["liquidity"])) if row.get("liquidity") is not None else None,
    )


def map_row_to_initialized_tick(row: Mapping[str, Any]) -> SimulateAprInitializedTick:
    return SimulateAprInitializedTick(
        tick_idx=int(row["tick_idx"]),
        liquidity_net=Decimal(str(row["liquidity_net"])),
    )
