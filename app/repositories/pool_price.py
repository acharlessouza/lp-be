from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text


@dataclass(frozen=True)
class PoolPricePointRow:
    timestamp: datetime
    price: Decimal


@dataclass(frozen=True)
class PoolPriceStatsRow:
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None


class PoolPriceRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_series(self, *, pool_id: int, days: int) -> list[PoolPricePointRow]:
        sql = """
            SELECT
                period_start AS timestamp,
                token1_price AS price
            FROM pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= (now() - (:days || ' days')::interval)
            ORDER BY period_start ASC
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), {"pool_id": pool_id, "days": days}).mappings().all()

        return [
            PoolPricePointRow(
                timestamp=row["timestamp"],
                price=Decimal(str(row["price"])),
            )
            for row in rows
            if row["timestamp"] is not None and row["price"] is not None
        ]

    def get_stats(self, *, pool_id: int, days: int) -> PoolPriceStatsRow:
        sql = """
            SELECT
                MIN(token1_price) AS min_price,
                MAX(token1_price) AS max_price,
                AVG(token1_price) AS avg_price
            FROM pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= (now() - (:days || ' days')::interval)
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id, "days": days}).mappings().first()
        if not row:
            return PoolPriceStatsRow(min_price=None, max_price=None, avg_price=None)
        return PoolPriceStatsRow(
            min_price=Decimal(str(row["min_price"])) if row["min_price"] is not None else None,
            max_price=Decimal(str(row["max_price"])) if row["max_price"] is not None else None,
            avg_price=Decimal(str(row["avg_price"])) if row["avg_price"] is not None else None,
        )
