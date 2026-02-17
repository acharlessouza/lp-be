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

    @staticmethod
    def _params(*, pool_address: str, chain_id: int, dex_id: int) -> dict[str, object]:
        return {
            "pool_address": pool_address.lower(),
            "chain_id": chain_id,
            "dex_id": dex_id,
        }

    def pool_exists(self, *, pool_address: str, chain_id: int, dex_id: int) -> bool:
        sql = """
            SELECT 1
            FROM public.pools p
            WHERE lower(p.pool_address) = :pool_address
              AND p.chain_id = :chain_id
              AND p.dex_id = :dex_id
            LIMIT 1
        """
        params = self._params(pool_address=pool_address, chain_id=chain_id, dex_id=dex_id)
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).first()
        return row is not None

    def get_series(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        days: int,
    ) -> list[PoolPricePoint]:
        sql = """
            SELECT
                to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC' AS timestamp,
                (
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS price
            FROM public.pool_state_snapshots s
            JOIN public.pools p
              ON p.dex_id = s.dex_id
             AND p.chain_id = s.chain_id
             AND lower(p.pool_address) = lower(s.pool_address)
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(s.pool_address) = :pool_address
              AND s.chain_id = :chain_id
              AND s.dex_id = :dex_id
              AND (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') >= (now() - (:days || ' days')::interval)
              AND s.sqrt_price_x96 IS NOT NULL
              AND s.sqrt_price_x96 ~ '^[0-9]+$'
              AND s.sqrt_price_x96 <> '0'
            ORDER BY (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') ASC
        """
        params = self._params(pool_address=pool_address, chain_id=chain_id, dex_id=dex_id)
        params["days"] = days
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            map_row_to_pool_price_point(row)
            for row in rows
            if row["timestamp"] is not None and row["price"] is not None
        ]

    def get_series_range(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        start: datetime,
        end: datetime,
    ) -> list[PoolPricePoint]:
        sql = """
            SELECT
                to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC' AS timestamp,
                (
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS price
            FROM public.pool_state_snapshots s
            JOIN public.pools p
              ON p.dex_id = s.dex_id
             AND p.chain_id = s.chain_id
             AND lower(p.pool_address) = lower(s.pool_address)
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(s.pool_address) = :pool_address
              AND s.chain_id = :chain_id
              AND s.dex_id = :dex_id
              AND (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') >= :start
              AND (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') <= :end
              AND s.sqrt_price_x96 IS NOT NULL
              AND s.sqrt_price_x96 ~ '^[0-9]+$'
              AND s.sqrt_price_x96 <> '0'
            ORDER BY (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') ASC
        """
        params = self._params(pool_address=pool_address, chain_id=chain_id, dex_id=dex_id)
        params.update({"start": start, "end": end})
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            map_row_to_pool_price_point(row)
            for row in rows
            if row["timestamp"] is not None and row["price"] is not None
        ]

    def get_stats(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        days: int,
    ) -> PoolPriceStats:
        sql = """
            SELECT
                MIN(
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS min_price,
                MAX(
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS max_price,
                AVG(
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS avg_price
            FROM public.pool_state_snapshots s
            JOIN public.pools p
              ON p.dex_id = s.dex_id
             AND p.chain_id = s.chain_id
             AND lower(p.pool_address) = lower(s.pool_address)
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(s.pool_address) = :pool_address
              AND s.chain_id = :chain_id
              AND s.dex_id = :dex_id
              AND (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') >= (now() - (:days || ' days')::interval)
              AND s.sqrt_price_x96 IS NOT NULL
              AND s.sqrt_price_x96 ~ '^[0-9]+$'
              AND s.sqrt_price_x96 <> '0'
        """
        params = self._params(pool_address=pool_address, chain_id=chain_id, dex_id=dex_id)
        params["days"] = days
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return PoolPriceStats(min_price=None, max_price=None, avg_price=None)
        return map_row_to_pool_price_stats(row)

    def get_stats_range(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        start: datetime,
        end: datetime,
    ) -> PoolPriceStats:
        sql = """
            SELECT
                MIN(
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS min_price,
                MAX(
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS max_price,
                AVG(
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS avg_price
            FROM public.pool_state_snapshots s
            JOIN public.pools p
              ON p.dex_id = s.dex_id
             AND p.chain_id = s.chain_id
             AND lower(p.pool_address) = lower(s.pool_address)
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(s.pool_address) = :pool_address
              AND s.chain_id = :chain_id
              AND s.dex_id = :dex_id
              AND (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') >= :start
              AND (to_timestamp(meta_block_timestamp) AT TIME ZONE 'UTC') <= :end
              AND s.sqrt_price_x96 IS NOT NULL
              AND s.sqrt_price_x96 ~ '^[0-9]+$'
              AND s.sqrt_price_x96 <> '0'
        """
        params = self._params(pool_address=pool_address, chain_id=chain_id, dex_id=dex_id)
        params.update({"start": start, "end": end})
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return PoolPriceStats(min_price=None, max_price=None, avg_price=None)
        return map_row_to_pool_price_stats(row)

    def get_latest_price(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> PoolCurrentPrice | None:
        sql = """
            SELECT
                (
                    power((s.sqrt_price_x96::numeric / power(2::numeric, 96)), 2)
                    * power(10::numeric, COALESCE(t0.decimals, 0) - COALESCE(t1.decimals, 0))
                ) AS token1_price,
                CASE
                    WHEN p.price_token0_per_token1 IS NOT NULL AND p.price_token0_per_token1 > 0
                    THEN p.price_token0_per_token1
                    ELSE NULL
                END AS token0_price,
                s.sqrt_price_x96
            FROM public.pool_state_snapshots s
            JOIN public.pools p
              ON p.dex_id = s.dex_id
             AND p.chain_id = s.chain_id
             AND lower(p.pool_address) = lower(s.pool_address)
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(s.pool_address) = :pool_address
              AND s.chain_id = :chain_id
              AND s.dex_id = :dex_id
              AND s.sqrt_price_x96 IS NOT NULL
              AND s.sqrt_price_x96 ~ '^[0-9]+$'
              AND s.sqrt_price_x96 <> '0'
            ORDER BY s.meta_block_number DESC
            LIMIT 1
        """
        params = self._params(pool_address=pool_address, chain_id=chain_id, dex_id=dex_id)
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if row:
            return map_row_to_current_pool_price(row)

        fallback_sql = """
            SELECT
                NULL AS token1_price,
                CASE
                    WHEN p.price_token0_per_token1 IS NOT NULL AND p.price_token0_per_token1 > 0
                    THEN p.price_token0_per_token1
                    ELSE NULL
                END AS token0_price,
                p.sqrt_price_x96
            FROM public.pools p
            WHERE lower(p.pool_address) = :pool_address
              AND p.chain_id = :chain_id
              AND p.dex_id = :dex_id
            LIMIT 1
        """
        with self._engine.connect() as conn:
            fallback_row = conn.execute(text(fallback_sql), params).mappings().first()
        if not fallback_row:
            return None
        return map_row_to_current_pool_price(fallback_row)
