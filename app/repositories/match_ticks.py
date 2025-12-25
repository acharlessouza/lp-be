from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text


@dataclass(frozen=True)
class PoolTickConfigRow:
    fee_tier: int
    token0_decimals: int
    token1_decimals: int


@dataclass(frozen=True)
class PoolLatestPriceRow:
    token0_price: Decimal | None
    token1_price: Decimal | None


class MatchTicksRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_pool_config(self, *, pool_id: int) -> PoolTickConfigRow | None:
        sql = """
            SELECT
                fee_tier,
                token0_decimals,
                token1_decimals
            FROM pools
            WHERE id = :pool_id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        return PoolTickConfigRow(
            fee_tier=row["fee_tier"],
            token0_decimals=row["token0_decimals"],
            token1_decimals=row["token1_decimals"],
        )

    def get_latest_prices(self, *, pool_id: int) -> PoolLatestPriceRow | None:
        sql = """
            SELECT
                token0_price,
                token1_price
            FROM pool_hours
            WHERE pool_id = :pool_id
            ORDER BY period_start DESC
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        token0_price = row["token0_price"]
        token1_price = row["token1_price"]
        return PoolLatestPriceRow(
            token0_price=Decimal(str(token0_price)) if token0_price is not None else None,
            token1_price=Decimal(str(token1_price)) if token1_price is not None else None,
        )
