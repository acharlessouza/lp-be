from __future__ import annotations

from sqlalchemy import text

from app.application.ports.simulate_apr_port import SimulateAprPort
from app.domain.entities.simulate_apr import (
    SimulateAprHourly,
    SimulateAprInitializedTick,
    SimulateAprPool,
    SimulateAprPoolState,
    SimulateAprSnapshotHourly,
)
from app.infrastructure.db.mappers.simulate_apr_mapper import (
    map_row_to_initialized_tick,
    map_row_to_simulate_apr_hourly,
    map_row_to_simulate_apr_pool,
    map_row_to_simulate_apr_pool_state,
    map_row_to_simulate_apr_snapshot_hourly,
)


class SqlSimulateAprRepository(SimulateAprPort):
    def __init__(self, engine):
        self._engine = engine

    def get_pool(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPool | None:
        sql = """
            SELECT
                p.dex_id,
                p.chain_id,
                p.pool_address,
                COALESCE(t0.decimals, 0) AS token0_decimals,
                COALESCE(t1.decimals, 0) AS token1_decimals,
                p.fee_tier,
                p.tick_spacing
            FROM public.pools p
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(p.pool_address) = :pool_address
              AND p.chain_id = :chain_id
              AND p.dex_id = :dex_id
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                },
            ).mappings().first()
        if not row:
            return None
        return map_row_to_simulate_apr_pool(row)

    def get_latest_pool_state(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPoolState | None:
        sql = """
            SELECT
                COALESCE(s.tick, p.tick) AS tick,
                COALESCE(s.sqrt_price_x96, p.sqrt_price_x96) AS sqrt_price_x96,
                p.price_token0_per_token1,
                COALESCE(s.liquidity, p.liquidity) AS liquidity
            FROM public.pools p
            LEFT JOIN LATERAL (
                SELECT
                    ss.tick,
                    ss.sqrt_price_x96,
                    ss.liquidity
                FROM public.pool_state_snapshots ss
                WHERE ss.dex_id = p.dex_id
                  AND ss.chain_id = p.chain_id
                  AND lower(ss.pool_address) = lower(p.pool_address)
                ORDER BY ss.meta_block_number DESC
                LIMIT 1
            ) s ON true
            WHERE lower(p.pool_address) = :pool_address
              AND p.chain_id = :chain_id
              AND p.dex_id = :dex_id
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                },
            ).mappings().first()
        if not row:
            return None
        return map_row_to_simulate_apr_pool_state(row)

    def get_pool_hourly(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        hours: int,
    ) -> list[SimulateAprHourly]:
        sql = """
            SELECT
                date_trunc('hour', h.hour_start) AS hour_ts,
                COALESCE(h.fees_usd, 0) AS fees_usd,
                h.volume_usd
            FROM public.pool_hourly h
            WHERE lower(h.pool_address) = :pool_address
              AND h.chain_id = :chain_id
              AND h.dex_id = :dex_id
              AND h.hour_start >= (now() - (:hours || ' hours')::interval)
            ORDER BY hour_ts ASC
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "hours": hours,
                },
            ).mappings().all()
        return [map_row_to_simulate_apr_hourly(row) for row in rows]

    def get_pool_state_snapshots_hourly(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        hours: int,
    ) -> list[SimulateAprSnapshotHourly]:
        sql = """
            WITH ranked AS (
                SELECT
                    -- NOTE: snapshot_at is the ingestion time. For simulation we need the on-chain
                    -- timestamp of the snapshot, stored in meta_block_timestamp.
                    date_trunc('hour', to_timestamp(s.meta_block_timestamp) AT TIME ZONE 'UTC') AS hour_ts,
                    s.tick,
                    row_number() OVER (
                        PARTITION BY date_trunc('hour', to_timestamp(s.meta_block_timestamp) AT TIME ZONE 'UTC')
                        ORDER BY s.meta_block_number DESC
                    ) AS rn
                FROM public.pool_state_snapshots s
                WHERE lower(s.pool_address) = :pool_address
                  AND s.chain_id = :chain_id
                  AND s.dex_id = :dex_id
                  AND (to_timestamp(s.meta_block_timestamp) AT TIME ZONE 'UTC') >= (now() - (:hours || ' hours')::interval)
            )
            SELECT hour_ts, tick
            FROM ranked
            WHERE rn = 1
            ORDER BY hour_ts ASC
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "hours": hours,
                },
            ).mappings().all()
        return [map_row_to_simulate_apr_snapshot_hourly(row) for row in rows]

    def get_initialized_ticks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        min_tick: int,
        max_tick: int,
    ) -> list[SimulateAprInitializedTick]:
        margin = 10_000
        tick_min = min_tick - margin
        tick_max = max_tick + margin
        sql = """
            SELECT
                t.tick_idx,
                t.liquidity_net
            FROM public.pool_ticks_initialized t
            WHERE lower(t.pool_address) = :pool_address
              AND t.chain_id = :chain_id
              AND t.dex_id = :dex_id
              AND t.liquidity_net IS NOT NULL
              AND t.tick_idx BETWEEN :tick_min AND :tick_max
            ORDER BY t.tick_idx ASC
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "tick_min": tick_min,
                    "tick_max": tick_max,
                },
            ).mappings().all()
        return [map_row_to_initialized_tick(row) for row in rows]
