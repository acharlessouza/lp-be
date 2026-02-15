from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text

from app.application.ports.liquidity_distribution_port import LiquidityDistributionPort
from app.domain.entities.liquidity_distribution import LiquidityDistributionPool, TickLiquidity
from app.infrastructure.db.mappers.liquidity_distribution_mapper import (
    map_row_to_liquidity_pool,
    map_row_to_tick_liquidity,
)


class SqlLiquidityDistributionRepository(LiquidityDistributionPort):
    def __init__(self, engine, min_tvl_usd: Decimal):
        self._engine = engine
        self._min_tvl_usd = min_tvl_usd

    def get_pool_by_id(self, *, pool_id: int) -> LiquidityDistributionPool | None:
        sql = """
            SELECT
                id,
                token0_symbol,
                token1_symbol,
                token0_decimals,
                token1_decimals,
                current_tick,
                onchain_liquidity
            FROM estrutura.pools
            WHERE id = :pool_id
              AND tvl_usd >= :min_tvl_usd
        """
        params = {
            "pool_id": pool_id,
            "min_tvl_usd": self._min_tvl_usd,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return None
        return map_row_to_liquidity_pool(row)

    def get_latest_period_start(self, *, pool_id: int) -> datetime | None:
        sql = """
            SELECT max(period_start) AS latest_period
            FROM estrutura.ticks
            WHERE pool_id = :pool_id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        return row["latest_period"] if row else None

    def get_ticks_by_period(self, *, pool_id: int, period_start: datetime) -> list[TickLiquidity]:
        sql = """
            SELECT
                tick_idx,
                liquidity_net
            FROM estrutura.ticks
            WHERE pool_id = :pool_id
              AND period_start = :period_start
            ORDER BY tick_idx
        """
        params = {
            "pool_id": pool_id,
            "period_start": period_start,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            map_row_to_tick_liquidity(row)
            for row in rows
            if row["liquidity_net"] is not None
        ]
