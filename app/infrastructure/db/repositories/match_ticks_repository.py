from __future__ import annotations

from sqlalchemy import text

from app.application.ports.match_ticks_port import MatchTicksPort
from app.domain.entities.match_ticks import MatchTicksLatestPrices, MatchTicksPoolConfig
from app.infrastructure.db.mappers.match_ticks_mapper import (
    map_row_to_match_ticks_latest_prices,
    map_row_to_match_ticks_pool_config,
)


class SqlMatchTicksRepository(MatchTicksPort):
    def __init__(self, engine):
        self._engine = engine

    def get_pool_config(self, *, pool_id: int) -> MatchTicksPoolConfig | None:
        sql = """
            SELECT
                fee_tier
            FROM pools
            WHERE id = :pool_id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        return map_row_to_match_ticks_pool_config(row)

    def get_latest_prices(self, *, pool_id: int) -> MatchTicksLatestPrices | None:
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
        return map_row_to_match_ticks_latest_prices(row)
