from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from app.domain.entities.match_ticks import MatchTicksLatestPrices, MatchTicksPoolConfig


def map_row_to_match_ticks_pool_config(row: Mapping[str, Any]) -> MatchTicksPoolConfig:
    return MatchTicksPoolConfig(
        fee_tier=row["fee_tier"],
    )


def map_row_to_match_ticks_latest_prices(row: Mapping[str, Any]) -> MatchTicksLatestPrices:
    return MatchTicksLatestPrices(
        token0_price=Decimal(str(row["token0_price"])) if row["token0_price"] is not None else None,
        token1_price=Decimal(str(row["token1_price"])) if row["token1_price"] is not None else None,
    )
