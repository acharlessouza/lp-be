from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.application.ports.radar_pools_port import RadarPoolsPort
from app.domain.entities.radar_pools import RadarPoolAggregate
from app.infrastructure.db.mappers.radar_pools_mapper import map_row_to_radar_pool_aggregate


class SqlRadarPoolsRepository(RadarPoolsPort):
    def __init__(self, engine):
        self._engine = engine

    def list_pools(
        self,
        *,
        start_dt: datetime,
        network_id: int | None,
        exchange_id: int | None,
        token_symbol: str | None,
    ) -> list[RadarPoolAggregate]:
        sql = """
            SELECT
                ABS(hashtext(p.dex_id::text || ':' || p.chain_id::text || ':' || lower(p.pool_address))::bigint) AS pool_id,
                p.pool_address,
                c.name AS network_name,
                d.name AS exchange_name,
                p.dex_id AS dex_id,
                p.chain_id AS chain_id,
                p.token0_address,
                p.token1_address,
                COALESCE(t0.symbol, p.token0_address) AS token0_symbol,
                COALESCE(t1.symbol, p.token1_address) AS token1_symbol,
                t0.icon_url AS token0_icon_url,
                t1.icon_url AS token1_icon_url,
                COALESCE(p.fee_tier, 0) AS fee_tier,
                AVG(ph.tvl_usd) AS avg_tvl_usd,
                SUM(COALESCE(ph.fees_usd, 0)) AS total_fees_usd,
                AVG(COALESCE(ph.fees_usd, 0)) AS avg_hourly_fees_usd,
                AVG(COALESCE(ph.volume_usd, 0)) AS avg_hourly_volume_usd,
                COUNT(*) AS samples
            FROM public.pools p
            JOIN public.pool_hourly ph
              ON ph.dex_id = p.dex_id
             AND ph.chain_id = p.chain_id
             AND lower(ph.pool_address) = lower(p.pool_address)
            JOIN public.chains c
              ON c.chain_id = p.chain_id
            JOIN public.dexes d
              ON d.dex_id = p.dex_id
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE ph.hour_start >= :start_dt
              AND (:network_id IS NULL OR p.chain_id = :network_id)
              AND (:exchange_id IS NULL OR p.dex_id = :exchange_id)
              AND (
                :token_symbol IS NULL
                OR UPPER(COALESCE(t0.symbol, p.token0_address)) = :token_symbol
                OR UPPER(COALESCE(t1.symbol, p.token1_address)) = :token_symbol
              )
            GROUP BY
                p.dex_id,
                p.chain_id,
                p.pool_address,
                p.token0_address,
                p.token1_address,
                c.name,
                d.name,
                COALESCE(t0.symbol, p.token0_address),
                COALESCE(t1.symbol, p.token1_address),
                t0.icon_url,
                t1.icon_url,
                COALESCE(p.fee_tier, 0)
        """
        params = {
            "start_dt": start_dt,
            "network_id": network_id,
            "exchange_id": exchange_id,
            "token_symbol": token_symbol,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [map_row_to_radar_pool_aggregate(row) for row in rows]
