from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.simulate_apr import SimulateAprInitializedTick
from app.domain.entities.simulate_apr_v2 import (
    SimulateAprV2Pool,
    SimulateAprV2PoolSnapshot,
    SimulateAprV2TickSnapshot,
)


def map_row_to_simulate_apr_v2_pool(row: Mapping[str, Any]) -> SimulateAprV2Pool:
    return SimulateAprV2Pool(
        dex_id=int(row["dex_id"]),
        chain_id=int(row["chain_id"]),
        pool_address=str(row["pool_address"]).lower(),
        token0_decimals=int(row["token0_decimals"] or 0),
        token1_decimals=int(row["token1_decimals"] or 0),
        fee_tier=int(row["fee_tier"]) if row["fee_tier"] is not None else None,
        tick_spacing=int(row["tick_spacing"]) if row["tick_spacing"] is not None else None,
    )


def map_row_to_simulate_apr_v2_pool_snapshot(row: Mapping[str, Any]) -> SimulateAprV2PoolSnapshot:
    return SimulateAprV2PoolSnapshot(
        block_number=int(row["meta_block_number"]),
        block_timestamp=int(row["meta_block_timestamp"]),
        tick=int(row["tick"]) if row["tick"] is not None else None,
        sqrt_price_x96=int(row["sqrt_price_x96"]) if row["sqrt_price_x96"] is not None else None,
        liquidity=Decimal(str(row["liquidity"])) if row["liquidity"] is not None else None,
        fee_growth_global0_x128=row["fee_growth_global0_x128"],
        fee_growth_global1_x128=row["fee_growth_global1_x128"],
    )


def map_row_to_simulate_apr_v2_tick_snapshot(row: Mapping[str, Any]) -> SimulateAprV2TickSnapshot:
    return SimulateAprV2TickSnapshot(
        block_number=int(row["block_number"]),
        tick_idx=int(row["tick_idx"]),
        fee_growth_outside0_x128=row["fee_growth_outside0_x128"],
        fee_growth_outside1_x128=row["fee_growth_outside1_x128"],
        liquidity_net=Decimal(str(row["liquidity_net"])) if row.get("liquidity_net") is not None else None,
        liquidity_gross=Decimal(str(row["liquidity_gross"])) if row.get("liquidity_gross") is not None else None,
    )


def map_row_to_initialized_tick(row: Mapping[str, Any]) -> SimulateAprInitializedTick:
    return SimulateAprInitializedTick(
        tick_idx=int(row["tick_idx"]),
        liquidity_net=Decimal(str(row["liquidity_net"])),
    )
