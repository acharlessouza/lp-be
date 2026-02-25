from __future__ import annotations

import logging

from sqlalchemy import text

from app.application.ports.pool_runtime_metadata_port import PoolRuntimeMetadataPort


logger = logging.getLogger(__name__)


class SqlPoolRuntimeMetadataRepository(PoolRuntimeMetadataPort):
    def __init__(self, engine):
        self._engine = engine

    def upsert_pool_activity(
        self,
        *,
        chain_id: int,
        dex_id: int,
        pool_address: str,
    ) -> None:
        sql = text(
            """
            INSERT INTO public.pool_activity (
                chain_id,
                dex_id,
                pool_address,
                last_access_at,
                access_count_1h,
                access_count_24h,
                updated_at
            )
            VALUES (
                :chain_id,
                :dex_id,
                :pool_address,
                now(),
                1,
                1,
                now()
            )
            ON CONFLICT (chain_id, dex_id, pool_address)
            DO UPDATE SET
                last_access_at = now(),
                access_count_1h = public.pool_activity.access_count_1h + 1,
                access_count_24h = public.pool_activity.access_count_24h + 1,
                updated_at = now()
            """
        )
        normalized_pool = pool_address.lower()
        with self._engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "pool_address": normalized_pool,
                },
            )
        logger.debug(
            "pool_runtime_metadata_repo: upsert_pool_activity pool=%s chain_id=%s dex_id=%s",
            normalized_pool,
            chain_id,
            dex_id,
        )

    def upsert_pool_ticks_window_refresh_state(
        self,
        *,
        chain_id: int,
        dex_id: int,
        pool_address: str,
        window_ticks: int,
        center_tick: int | None,
        last_pool_tick: int | None,
        last_block_number: int | None = None,
        source: str = "simulate_apr_v2",
    ) -> None:
        sql = text(
            """
            INSERT INTO public.pool_ticks_window_refresh_state (
                chain_id,
                dex_id,
                pool_address,
                window_ticks,
                center_tick,
                last_pool_tick,
                last_refreshed_at,
                last_block_number,
                source,
                updated_at
            )
            VALUES (
                :chain_id,
                :dex_id,
                :pool_address,
                :window_ticks,
                :center_tick,
                :last_pool_tick,
                now(),
                :last_block_number,
                :source,
                now()
            )
            ON CONFLICT (chain_id, dex_id, pool_address, window_ticks)
            DO UPDATE SET
                center_tick = EXCLUDED.center_tick,
                last_pool_tick = EXCLUDED.last_pool_tick,
                last_block_number = EXCLUDED.last_block_number,
                last_refreshed_at = now(),
                source = EXCLUDED.source,
                updated_at = now()
            """
        )
        normalized_pool = pool_address.lower()
        with self._engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "chain_id": chain_id,
                    "dex_id": dex_id,
                    "pool_address": normalized_pool,
                    "window_ticks": window_ticks,
                    "center_tick": center_tick,
                    "last_pool_tick": last_pool_tick,
                    "last_block_number": last_block_number,
                    "source": source,
                },
            )
        logger.debug(
            "pool_runtime_metadata_repo: upsert_ticks_window_refresh_state pool=%s chain_id=%s dex_id=%s window_ticks=%s source=%s",
            normalized_pool,
            chain_id,
            dex_id,
            window_ticks,
            source,
        )
