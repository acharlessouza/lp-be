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
        # Mantem compatibilidade com o pool_id numerico exposto na API.
        pool_id_expr = """
            (
                (
                    'x' || substr(
                        md5(
                            p.dex_id::text || ':' || p.chain_id::text || ':' || lower(p.pool_address)
                        ),
                        1,
                        8
                    )
                )::bit(32)::int & 2147483647
            )
        """
        sql = """
            SELECT
                {pool_id_expr} AS id,
                COALESCE(t0.symbol, p.token0_address) AS token0_symbol,
                COALESCE(t1.symbol, p.token1_address) AS token1_symbol,
                COALESCE(t0.decimals, 0) AS token0_decimals,
                COALESCE(t1.decimals, 0) AS token1_decimals,
                p.fee_tier AS fee_tier,
                p.tick_spacing AS tick_spacing,
                p.tick AS pool_tick,
                COALESCE(ss.tick, p.tick) AS current_tick,
                p.price_token0_per_token1 AS current_price_token1_per_token0,
                COALESCE(ss.liquidity, p.liquidity) AS onchain_liquidity
            FROM public.pools p
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            LEFT JOIN LATERAL (
                SELECT
                    s.tick,
                    s.liquidity
                FROM public.pool_state_snapshots s
                WHERE s.dex_id = p.dex_id
                  AND s.chain_id = p.chain_id
                  AND lower(s.pool_address) = lower(p.pool_address)
                ORDER BY s.meta_block_number DESC
                LIMIT 1
            ) ss ON true
            WHERE {pool_id_expr} = :pool_id
              AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
            LIMIT 1
        """.format(pool_id_expr=pool_id_expr)
        params = {
            "pool_id": pool_id,
            "min_tvl_usd": self._min_tvl_usd,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return None
        return map_row_to_liquidity_pool(row)

    def find_pools_by_address(
        self,
        *,
        pool_address: str,
        chain_id: int | None = None,
        dex_id: int | None = None,
    ) -> list[LiquidityDistributionPool]:
        pool_id_expr = """
            (
                (
                    'x' || substr(
                        md5(
                            p.dex_id::text || ':' || p.chain_id::text || ':' || lower(p.pool_address)
                        ),
                        1,
                        8
                    )
                )::bit(32)::int & 2147483647
            )
        """
        sql = """
            SELECT
                {pool_id_expr} AS id,
                COALESCE(t0.symbol, p.token0_address) AS token0_symbol,
                COALESCE(t1.symbol, p.token1_address) AS token1_symbol,
                COALESCE(t0.decimals, 0) AS token0_decimals,
                COALESCE(t1.decimals, 0) AS token1_decimals,
                p.fee_tier AS fee_tier,
                p.tick_spacing AS tick_spacing,
                p.tick AS pool_tick,
                COALESCE(ss.tick, p.tick) AS current_tick,
                p.price_token0_per_token1 AS current_price_token1_per_token0,
                COALESCE(ss.liquidity, p.liquidity) AS onchain_liquidity
            FROM public.pools p
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            LEFT JOIN LATERAL (
                SELECT
                    s.tick,
                    s.liquidity
                FROM public.pool_state_snapshots s
                WHERE s.dex_id = p.dex_id
                  AND s.chain_id = p.chain_id
                  AND lower(s.pool_address) = lower(p.pool_address)
                ORDER BY s.meta_block_number DESC
                LIMIT 1
            ) ss ON true
            WHERE lower(p.pool_address) = :pool_address
              AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
              AND (:chain_id IS NULL OR p.chain_id = :chain_id)
              AND (:dex_id IS NULL OR p.dex_id = :dex_id)
            ORDER BY COALESCE(p.tvl_usd, 0) DESC, p.dex_id, p.chain_id
        """.format(pool_id_expr=pool_id_expr)
        params = {
            "pool_address": pool_address.lower(),
            "min_tvl_usd": self._min_tvl_usd,
            "chain_id": chain_id,
            "dex_id": dex_id,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [map_row_to_liquidity_pool(row) for row in rows]

    def get_latest_period_start(self, *, pool_id: int) -> datetime | None:
        pool_id_expr = """
            (
                (
                    'x' || substr(
                        md5(
                            s.dex_id::text || ':' || s.chain_id::text || ':' || lower(s.pool_address)
                        ),
                        1,
                        8
                    )
                )::bit(32)::int & 2147483647
            )
        """
        sql = """
            SELECT max(period_start) AS latest_period
            FROM (
                SELECT max(s.snapshot_at) AS period_start
                FROM public.pool_state_snapshots s
                WHERE {pool_id_expr} = :pool_id
            ) latest
        """.format(pool_id_expr=pool_id_expr)
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        return row["latest_period"] if row else None

    def get_ticks_by_period(self, *, pool_id: int, period_start: datetime) -> list[TickLiquidity]:
        _ = period_start
        pool_id_expr = """
            (
                (
                    'x' || substr(
                        md5(
                            t.dex_id::text || ':' || t.chain_id::text || ':' || lower(t.pool_address)
                        ),
                        1,
                        8
                    )
                )::bit(32)::int & 2147483647
            )
        """
        sql = """
            SELECT
                tick_idx,
                liquidity_net
            FROM public.pool_ticks_initialized t
            WHERE {pool_id_expr} = :pool_id
            ORDER BY tick_idx
        """.format(pool_id_expr=pool_id_expr)
        params = {
            "pool_id": pool_id,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            map_row_to_tick_liquidity(row)
            for row in rows
            if row["liquidity_net"] is not None
        ]
