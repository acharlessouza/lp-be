from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.discover_pools import DiscoverPoolAggregate


def map_row_to_discover_pool_aggregate(row: Mapping[str, Any]) -> DiscoverPoolAggregate:
    return DiscoverPoolAggregate(
        pool_id=row["pool_id"],
        pool_address=row["pool_address"],
        network_name=row["network_name"],
        exchange_name=row["exchange_name"],
        token0_symbol=row["token0_symbol"],
        token1_symbol=row["token1_symbol"],
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
