from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import date

from sqlalchemy import text


@dataclass(frozen=True)
class LiquidityDistributionRow:
    tick_idx: int
    liquidity_active: Decimal
    price_token1_per_token0: Decimal
    token0_symbol: str
    token1_symbol: str


class LiquidityDistributionRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_rows(
        self,
        *,
        pool_id: int,
        snapshot_date: date,
        min_tick: int,
        max_tick: int,
    ) -> list[LiquidityDistributionRow]:
        sql = """
            WITH liquidity AS (
                SELECT
                    ts.pool_id,
                    ts.tick_idx,
                    SUM(ts.liquidity_net) OVER (
                        PARTITION BY ts.pool_id
                        ORDER BY ts.tick_idx
                    ) AS liquidity_active
                FROM tick_snapshots ts
                WHERE ts.pool_id = :pool_id
                  AND ts.date = :snapshot_date
            )
            SELECT
                l.tick_idx,
                l.liquidity_active,
                exp(l.tick_idx * ln(1.0001))
                  * power(10, p.token0_decimals - p.token1_decimals)
                  AS price_token1_per_token0,
                p.token0_symbol,
                p.token1_symbol
            FROM liquidity l
            JOIN pools p ON p.id = l.pool_id
            WHERE l.tick_idx BETWEEN :min_tick AND :max_tick
            ORDER BY l.tick_idx
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {
                    "pool_id": pool_id,
                    "snapshot_date": snapshot_date,
                    "min_tick": min_tick,
                    "max_tick": max_tick,
                },
            ).mappings().all()

        return [
            LiquidityDistributionRow(
                tick_idx=row["tick_idx"],
                liquidity_active=Decimal(str(row["liquidity_active"])),
                price_token1_per_token0=Decimal(str(row["price_token1_per_token0"])),
                token0_symbol=row["token0_symbol"],
                token1_symbol=row["token1_symbol"],
            )
            for row in rows
            if row["liquidity_active"] is not None
        ]
