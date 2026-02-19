from __future__ import annotations

import logging

from sqlalchemy import bindparam, text

from app.application.ports.simulate_apr_v2_port import SimulateAprV2Port
from app.domain.entities.simulate_apr import SimulateAprInitializedTick
from app.domain.entities.simulate_apr_v2 import (
    SimulateAprV2Pool,
    SimulateAprV2PoolSnapshot,
    SimulateAprV2TickSnapshot,
)
from app.infrastructure.db.mappers.simulate_apr_v2_mapper import (
    map_row_to_initialized_tick,
    map_row_to_simulate_apr_v2_pool,
    map_row_to_simulate_apr_v2_pool_snapshot,
    map_row_to_simulate_apr_v2_tick_snapshot,
)


logger = logging.getLogger(__name__)


class SqlSimulateAprV2Repository(SimulateAprV2Port):
    def __init__(self, engine):
        self._engine = engine

    def get_pool(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprV2Pool | None:
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
            logger.warning(
                "simulate_apr_v2_repo: pool_not_found pool=%s chain_id=%s dex_id=%s",
                pool_address.lower(),
                chain_id,
                dex_id,
            )
            return None
        return map_row_to_simulate_apr_v2_pool(row)

    def get_latest_pool_snapshot(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprV2PoolSnapshot | None:
        sql = """
            SELECT
                meta_block_number,
                meta_block_timestamp,
                tick,
                sqrt_price_x96,
                liquidity,
                fee_growth_global0_x128,
                fee_growth_global1_x128
            FROM public.pool_state_snapshots
            WHERE dex_id = :dex_id
              AND chain_id = :chain_id
              AND lower(pool_address) = :pool_address
            ORDER BY meta_block_timestamp DESC
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
            logger.warning(
                "simulate_apr_v2_repo: latest_snapshot_not_found pool=%s chain_id=%s dex_id=%s",
                pool_address.lower(),
                chain_id,
                dex_id,
            )
            return None
        return map_row_to_simulate_apr_v2_pool_snapshot(row)

    def get_lookback_pool_snapshot(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        target_timestamp: int,
    ) -> SimulateAprV2PoolSnapshot | None:
        sql = """
            SELECT
                meta_block_number,
                meta_block_timestamp,
                tick,
                sqrt_price_x96,
                liquidity,
                fee_growth_global0_x128,
                fee_growth_global1_x128
            FROM public.pool_state_snapshots
            WHERE dex_id = :dex_id
              AND chain_id = :chain_id
              AND lower(pool_address) = :pool_address
              AND meta_block_timestamp <= :target_timestamp
            ORDER BY meta_block_timestamp DESC
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "target_timestamp": target_timestamp,
                },
            ).mappings().first()
        if not row:
            logger.warning(
                "simulate_apr_v2_repo: lookback_snapshot_not_found pool=%s chain_id=%s dex_id=%s target_timestamp=%s",
                pool_address.lower(),
                chain_id,
                dex_id,
                target_timestamp,
            )
            return None
        return map_row_to_simulate_apr_v2_pool_snapshot(row)

    def get_tick_snapshots_for_blocks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> list[SimulateAprV2TickSnapshot]:
        sql = text(
            """
            SELECT
                block_number,
                tick_idx,
                fee_growth_outside0_x128,
                fee_growth_outside1_x128
            FROM apr_exact.tick_snapshot
            WHERE dex_id = :dex_id
              AND chain_id = :chain_id
              AND lower(pool_address) = :pool_address
              AND block_number IN :block_numbers
              AND tick_idx IN :tick_indices
            """
        ).bindparams(
            bindparam("block_numbers", expanding=True),
            bindparam("tick_indices", expanding=True),
        )

        with self._engine.connect() as conn:
            rows = conn.execute(
                sql,
                {
                    "pool_address": pool_address.lower(),
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "block_numbers": block_numbers,
                    "tick_indices": tick_indices,
                },
            ).mappings().all()

        expected_count = len(set(block_numbers)) * len(set(tick_indices))
        if len(rows) < expected_count:
            logger.warning(
                "simulate_apr_v2_repo: missing_tick_snapshots pool=%s chain_id=%s dex_id=%s blocks=%s ticks=%s expected=%s found=%s",
                pool_address.lower(),
                chain_id,
                dex_id,
                sorted(set(block_numbers)),
                sorted(set(tick_indices)),
                expected_count,
                len(rows),
            )

        return [map_row_to_simulate_apr_v2_tick_snapshot(row) for row in rows]

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
        if not rows:
            logger.warning(
                "simulate_apr_v2_repo: initialized_ticks_not_found pool=%s chain_id=%s dex_id=%s tick_min=%s tick_max=%s",
                pool_address.lower(),
                chain_id,
                dex_id,
                tick_min,
                tick_max,
            )
        return [map_row_to_initialized_tick(row) for row in rows]
