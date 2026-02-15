from __future__ import annotations

from sqlalchemy import text

from app.application.ports.allocation_pool_port import AllocationPoolPort
from app.domain.entities.pool import Pool
from app.infrastructure.db.mappers.allocation_pool_mapper import map_row_to_pool


class SqlAllocationPoolRepository(AllocationPoolPort):
    def __init__(self, engine):
        self._engine = engine

    def get_by_address(self, *, pool_address: str, network: str) -> Pool | None:
        sql = """
            SELECT
                c.chain_key AS network,
                p.pool_address,
                COALESCE(p.fee_tier, 0) AS fee_tier,
                p.token0_address,
                COALESCE(t0.symbol, p.token0_address) AS token0_symbol,
                p.token1_address,
                COALESCE(t1.symbol, p.token1_address) AS token1_symbol
            FROM public.pools p
            JOIN public.chains c
              ON c.chain_id = p.chain_id
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(p.pool_address) = :pool_address
              AND lower(c.chain_key) = :network
            ORDER BY p.dex_id, p.chain_id, p.pool_address
            LIMIT 1
        """
        params = {
            "pool_address": pool_address.lower(),
            "network": network.lower(),
        }

        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()

        if not row:
            return None

        return map_row_to_pool(row)
