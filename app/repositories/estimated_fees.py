from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text


@dataclass(frozen=True)
class EstimatedFeesAggregates:
    pool_fees_in_range: Decimal | None
    avg_pool_liquidity_in_range: Decimal | None
    hours_in_range: int


class EstimatedFeesRepository:
    def __init__(self, engine):
        self._engine = engine

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
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "pool_id": pool_id,
                    "days": days,
                    "min_price": min_price,
                    "max_price": max_price,
                },
            ).mappings().first()

        if not row:
            return EstimatedFeesAggregates(
                pool_fees_in_range=None,
                avg_pool_liquidity_in_range=None,
                hours_in_range=0,
            )

        return EstimatedFeesAggregates(
            pool_fees_in_range=Decimal(str(row["pool_fees_in_range"]))
            if row["pool_fees_in_range"] is not None
            else None,
            avg_pool_liquidity_in_range=Decimal(str(row["avg_pool_liquidity_in_range"]))
            if row["avg_pool_liquidity_in_range"] is not None
            else None,
            hours_in_range=int(row["hours_in_range"] or 0),
        )
