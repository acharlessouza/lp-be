from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from app.application.ports.estimated_fees_port import EstimatedFeesPort
from app.domain.entities.estimated_fees import EstimatedFeesAggregates, EstimatedFeesPool
from app.domain.entities.pool_price import PoolCurrentPrice
from app.infrastructure.db.mappers.estimated_fees_mapper import (
    map_row_to_estimated_fees_aggregates,
    map_row_to_estimated_fees_pool,
)
from app.infrastructure.db.mappers.pool_price_mapper import map_row_to_current_pool_price


class SqlEstimatedFeesRepository(EstimatedFeesPort):
    def __init__(self, engine):
        self._engine = engine

    def get_pool_by_id(self, *, pool_id: int) -> EstimatedFeesPool | None:
        sql = """
            SELECT
                id,
                token0_decimals,
                token1_decimals
            FROM estrutura.pools
            WHERE id = :pool_id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        return map_row_to_estimated_fees_pool(row)

    def get_aggregates(
        self,
        *,
        pool_id: int,
        days: int,
        min_price: Decimal,
        max_price: Decimal,
    ) -> EstimatedFeesAggregates:
        sql = """
            SELECT
                SUM(fees_usd) AS pool_fees_in_range,
                AVG(liquidity) AS avg_pool_liquidity_in_range,
                COUNT(*) AS hours_in_range
            FROM pool_hours
            WHERE pool_id = :pool_id
              AND period_start >= (now() - (:days || ' days')::interval)
              AND token1_price BETWEEN :min_price AND :max_price
        """
        params = {
            "pool_id": pool_id,
            "days": days,
            "min_price": min_price,
            "max_price": max_price,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return EstimatedFeesAggregates(
                pool_fees_in_range=None,
                avg_pool_liquidity_in_range=None,
                hours_in_range=0,
            )
        return map_row_to_estimated_fees_aggregates(row)

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
