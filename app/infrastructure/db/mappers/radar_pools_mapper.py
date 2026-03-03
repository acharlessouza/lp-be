from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.radar_pools import RadarPoolAggregate


def map_row_to_radar_pool_aggregate(row: Mapping[str, Any]) -> RadarPoolAggregate:
    return RadarPoolAggregate(
        pool_id=row["pool_id"],
        pool_address=row["pool_address"],
        network_name=row["network_name"],
        exchange_name=row["exchange_name"],
        dex_id=int(row["dex_id"]),
        chain_id=int(row["chain_id"]),
        token0_address=row["token0_address"],
        token1_address=row["token1_address"],
        token0_symbol=row["token0_symbol"],
        token1_symbol=row["token1_symbol"],
        token0_icon_url=row.get("token0_icon_url"),
        token1_icon_url=row.get("token1_icon_url"),
        fee_tier=row["fee_tier"],
        avg_tvl_usd=Decimal(str(row["avg_tvl_usd"])) if row["avg_tvl_usd"] is not None else None,
        total_fees_usd=Decimal(str(row["total_fees_usd"])) if row["total_fees_usd"] is not None else None,
        avg_hourly_fees_usd=Decimal(str(row["avg_hourly_fees_usd"]))
        if row["avg_hourly_fees_usd"] is not None
        else None,
        avg_hourly_volume_usd=Decimal(str(row["avg_hourly_volume_usd"]))
        if row["avg_hourly_volume_usd"] is not None
        else None,
        samples=int(row["samples"] or 0),
    )
