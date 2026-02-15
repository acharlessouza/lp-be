from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.entities.pool import Pool


def map_row_to_pool(row: Mapping[str, Any]) -> Pool:
    return Pool(
        network=row["network"],
        pool_address=row["pool_address"],
        fee_tier=row["fee_tier"],
        token0_address=row["token0_address"],
        token0_symbol=row["token0_symbol"],
        token1_address=row["token1_address"],
        token1_symbol=row["token1_symbol"],
    )
