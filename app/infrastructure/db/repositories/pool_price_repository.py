from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.application.ports.pool_price_port import PoolPricePort
from app.domain.entities.pool_price import PoolCurrentPrice, PoolPricePoint, PoolPriceStats
from app.infrastructure.db.mappers.pool_price_mapper import (
    map_row_to_current_pool_price,
    map_row_to_pool_price_point,
    map_row_to_pool_price_stats,
)


class SqlPoolPriceRepository(PoolPricePort):
    def __init__(self, engine):
        self._engine = engine

    def pool_exists(self, *, pool_id: int) -> bool:
        sql = """
            SELECT 1
            FROM estrutura.pools
            WHERE id = :pool_id
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).first()
        return row is not None

    def get_series(self, *, pool_id: int, days: int) -> list[PoolPricePoint]:
        sql = """
            SELECT
                period_start AS timestamp,
                token1_price AS price
            FROM estrutura.pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= (now() - (:days || ' days')::interval)
            ORDER BY period_start ASC
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), {"pool_id": pool_id, "days": days}).mappings().all()
        return [
            map_row_to_pool_price_point(row)
            for row in rows
            if row["timestamp"] is not None and row["price"] is not None
        ]

    def get_series_range(
        self,
        *,
        pool_id: int,
        start: datetime,
        end: datetime,
    ) -> list[PoolPricePoint]:
        sql = """
            SELECT
                period_start AS timestamp,
                token1_price AS price
            FROM estrutura.pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= :start
              AND period_start <= :end
            ORDER BY period_start ASC
        """
        params = {
            "pool_id": pool_id,
            "start": start,
            "end": end,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            map_row_to_pool_price_point(row)
            for row in rows
            if row["timestamp"] is not None and row["price"] is not None
        ]

    def get_stats(self, *, pool_id: int, days: int) -> PoolPriceStats:
        sql = """
            SELECT
                MIN(token1_price) AS min_price,
                MAX(token1_price) AS max_price,
                AVG(token1_price) AS avg_price
            FROM estrutura.pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= (now() - (:days || ' days')::interval)
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id, "days": days}).mappings().first()
        if not row:
            return PoolPriceStats(min_price=None, max_price=None, avg_price=None)
        return map_row_to_pool_price_stats(row)

    def get_stats_range(self, *, pool_id: int, start: datetime, end: datetime) -> PoolPriceStats:
        sql = """
            SELECT
                MIN(token1_price) AS min_price,
                MAX(token1_price) AS max_price,
                AVG(token1_price) AS avg_price
            FROM estrutura.pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= :start
              AND period_start <= :end
        """
        params = {
            "pool_id": pool_id,
            "start": start,
            "end": end,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return PoolPriceStats(min_price=None, max_price=None, avg_price=None)
        return map_row_to_pool_price_stats(row)

    def get_latest_price(self, *, pool_id: int) -> PoolCurrentPrice | None:
        sql = """
            SELECT
                token1_price,
                token0_price,
                sqrt_price_x96
            FROM estrutura.pool_hours
            WHERE pool_id = :pool_id
            ORDER BY period_start DESC
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        return map_row_to_current_pool_price(row)
