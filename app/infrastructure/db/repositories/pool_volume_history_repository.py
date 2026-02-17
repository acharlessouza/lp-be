from __future__ import annotations

from sqlalchemy import text

from app.application.ports.pool_volume_history_port import PoolVolumeHistoryPort
from app.domain.entities.pool_volume_history import (
    PoolVolumeHistoryPoint,
    PoolVolumeHistorySummaryBase,
    PoolVolumeHistorySummaryPremium,
)
from app.infrastructure.db.mappers.pool_volume_history_mapper import (
    map_row_to_pool_volume_history_point,
    map_row_to_pool_volume_history_summary_base,
    map_row_to_pool_volume_history_summary_premium,
)


class SqlPoolVolumeHistoryRepository(PoolVolumeHistoryPort):
    def __init__(self, engine):
        self._engine = engine

    def list_daily_volume_history(
        self,
        *,
        pool_address: str,
        days: int,
        chain_id: int | None,
        dex_id: int | None,
    ) -> list[PoolVolumeHistoryPoint]:
        sql = """
            WITH daily AS (
              SELECT
                date_trunc('day', h.hour_start AT TIME ZONE 'UTC') AS day_utc,
                SUM(h.volume_usd)            AS volume_usd,
                SUM(COALESCE(h.fees_usd, 0)) AS fees_usd
              FROM public.pool_hourly h
              WHERE lower(h.pool_address) = :pool_address
                AND (:chain_id IS NULL OR h.chain_id = :chain_id)
                AND (:dex_id IS NULL OR h.dex_id = :dex_id)
                AND h.hour_start >= (
                    date_trunc('day', now() AT TIME ZONE 'UTC')
                    - (CAST(:days AS int) * interval '1 day')
                )
              GROUP BY 1
            )
            SELECT
              TO_CHAR(
                ((day_utc AT TIME ZONE 'UTC') AT TIME ZONE 'America/Sao_Paulo'),
                'YYYY-MM-DD'
              )                                    AS time,
              volume_usd::numeric                 AS value,
              fees_usd::numeric                   AS fees_usd
            FROM daily
            ORDER BY day_utc
        """
        params = {
            "pool_address": pool_address.lower(),
            "days": days - 1,
            "chain_id": chain_id,
            "dex_id": dex_id,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [map_row_to_pool_volume_history_point(row) for row in rows]

    def get_summary_base(
        self,
        *,
        pool_address: str,
        days: int,
        chain_id: int | None,
        dex_id: int | None,
    ) -> PoolVolumeHistorySummaryBase:
        sql = """
            WITH bounds AS (
              SELECT
                date_trunc('day', now() AT TIME ZONE 'UTC') AS end_ts,
                date_trunc('day', now() AT TIME ZONE 'UTC') - (CAST(:days AS int) * interval '1 day') AS start_ts
            ),
            pool_meta AS (
              SELECT
                t0.symbol AS token0_symbol,
                t1.symbol AS token1_symbol
              FROM public.pools p
              LEFT JOIN public.tokens t0
                ON t0.chain_id = p.chain_id
               AND lower(t0.address) = lower(p.token0_address)
              LEFT JOIN public.tokens t1
                ON t1.chain_id = p.chain_id
               AND lower(t1.address) = lower(p.token1_address)
              WHERE lower(p.pool_address) = :pool_address
                AND (:chain_id IS NULL OR p.chain_id = :chain_id)
                AND (:dex_id IS NULL OR p.dex_id = :dex_id)
              LIMIT 1
            ),
            last_tvl AS (
              SELECT h.tvl_usd
              FROM public.pool_hourly h, bounds b
              WHERE lower(h.pool_address) = :pool_address
                AND (:chain_id IS NULL OR h.chain_id = :chain_id)
                AND (:dex_id IS NULL OR h.dex_id = :dex_id)
                AND h.hour_start < b.end_ts
              ORDER BY h.hour_start DESC
              LIMIT 1
            ),
            daily AS (
              SELECT
                date_trunc('day', h.hour_start AT TIME ZONE 'UTC') AS day_utc,
                SUM(h.volume_usd)            AS volume_usd,
                SUM(COALESCE(h.fees_usd, 0)) AS fees_usd
              FROM public.pool_hourly h, bounds b
              WHERE lower(h.pool_address) = :pool_address
                AND (:chain_id IS NULL OR h.chain_id = :chain_id)
                AND (:dex_id IS NULL OR h.dex_id = :dex_id)
                AND h.hour_start >= b.start_ts
                AND h.hour_start <  b.end_ts
              GROUP BY 1
            ),
            agg AS (
              SELECT
                AVG(d.fees_usd)   AS avg_daily_fees_usd,
                AVG(d.volume_usd) AS avg_daily_volume_usd
              FROM daily d
            )
            SELECT
              (SELECT tvl_usd FROM last_tvl) AS tvl_usd,
              a.avg_daily_fees_usd,
              a.avg_daily_volume_usd,
              pm.token0_symbol,
              pm.token1_symbol
            FROM agg a
            LEFT JOIN pool_meta pm ON true
        """
        params = {
            "pool_address": pool_address.lower(),
            "days": days,
            "chain_id": chain_id,
            "dex_id": dex_id,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if row is None:
            return PoolVolumeHistorySummaryBase(
                tvl_usd=None,
                avg_daily_fees_usd=None,
                avg_daily_volume_usd=None,
                token0_symbol=None,
                token1_symbol=None,
            )
        return map_row_to_pool_volume_history_summary_base(row)

    def get_summary_premium(
        self,
        *,
        exchange: str,
        symbol0: str,
        symbol1: str | None,
        days: int,
    ) -> PoolVolumeHistorySummaryPremium:

        print(">>>>.", symbol0, symbol1)
        if symbol1 is None:
            sql = """
                WITH bounds AS (
                  SELECT
                    (date_trunc('day', now() AT TIME ZONE 'UTC') - (CAST(:days AS int) * interval '1 day'))::date AS start_date,
                    (date_trunc('day', now() AT TIME ZONE 'UTC'))::date AS end_date
                ),
                vol AS (
                  SELECT
                    AVG(((high - low) / NULLIF(high, 0)) * 100.0) AS price_volatility_pct
                  FROM public.crypto_ohlc_daily c, bounds b
                  WHERE c.exchange = :exchange
                    AND c.symbol = :symbol0
                    AND c.timeframe = '1d'
                    AND c.day_start >= b.start_date
                    AND c.day_start <  b.end_date
                    AND c.high IS NOT NULL
                    AND c.low  IS NOT NULL
                ),
                minmax AS (
                  SELECT
                    MIN(c.low)  AS min_price,
                    MAX(c.high) AS max_price
                  FROM public.crypto_ohlc_daily c, bounds b
                  WHERE c.exchange = :exchange
                    AND c.symbol = :symbol0
                    AND c.timeframe = '1d'
                    AND c.day_start >= b.start_date
                    AND c.day_start <  b.end_date
                    AND c.low  IS NOT NULL
                    AND c.high IS NOT NULL
                )
                SELECT
                  v.price_volatility_pct,
                  NULL::numeric AS correlation,
                  CASE
                    WHEN m.min_price IS NOT NULL AND m.max_price IS NOT NULL AND m.min_price > 0 AND m.max_price > 0
                    THEN sqrt(m.min_price * m.max_price)
                    ELSE NULL
                  END AS geometric_mean_price
                FROM vol v
                CROSS JOIN minmax m
            """
            params = {
                "exchange": exchange,
                "symbol0": symbol0,
                "days": days,
            }
            with self._engine.connect() as conn:
                row = conn.execute(text(sql), params).mappings().first()
            if row is None:
                return PoolVolumeHistorySummaryPremium(
                    price_volatility_pct=None,
                    correlation=None,
                    geometric_mean_price=None,
                )
            return map_row_to_pool_volume_history_summary_premium(row)

        sql = """
            WITH bounds AS (
              SELECT
                (date_trunc('day', now() AT TIME ZONE 'UTC') - (CAST(:days AS int) * interval '1 day'))::date AS start_date,
                (date_trunc('day', now() AT TIME ZONE 'UTC'))::date AS end_date
            ),
            vol AS (
              SELECT
                AVG(((high - low) / NULLIF(high, 0)) * 100.0) AS price_volatility_pct
              FROM public.crypto_ohlc_daily c, bounds b
              WHERE c.exchange = :exchange
                AND c.symbol = :symbol0
                AND c.timeframe = '1d'
                AND c.day_start >= b.start_date
                AND c.day_start <  b.end_date
                AND c.high IS NOT NULL
                AND c.low  IS NOT NULL
            ),
            minmax AS (
              SELECT
                MIN(c.low)  AS min_price,
                MAX(c.high) AS max_price
              FROM public.crypto_ohlc_daily c, bounds b
              WHERE c.exchange = :exchange
                AND c.symbol = :symbol0
                AND c.timeframe = '1d'
                AND c.day_start >= b.start_date
                AND c.day_start <  b.end_date
                AND c.low  IS NOT NULL
                AND c.high IS NOT NULL
            ),
            corr_data AS (
              WITH a AS (
                SELECT day_start, close::double precision AS c0
                FROM public.crypto_ohlc_daily c, bounds b
                WHERE c.exchange = :exchange
                  AND c.symbol = :symbol0
                  AND c.timeframe = '1d'
                  AND c.day_start >= b.start_date
                  AND c.day_start <  b.end_date
                  AND c.close IS NOT NULL
              ),
              b AS (
                SELECT day_start, close::double precision AS c1
                FROM public.crypto_ohlc_daily c, bounds b2
                WHERE c.exchange = :exchange
                  AND c.symbol = :symbol1
                  AND c.timeframe = '1d'
                  AND c.day_start >= b2.start_date
                  AND c.day_start <  b2.end_date
                  AND c.close IS NOT NULL
              ),
              joined AS (
                SELECT a.day_start, a.c0, b.c1
                FROM a JOIN b USING (day_start)
              )
              SELECT corr(c0, c1) AS correlation
              FROM joined
            )
            SELECT
              v.price_volatility_pct,
              c.correlation,
              CASE
                WHEN m.min_price IS NOT NULL AND m.max_price IS NOT NULL AND m.min_price > 0 AND m.max_price > 0
                THEN sqrt(m.min_price * m.max_price)
                ELSE NULL
              END AS geometric_mean_price
            FROM vol v
            CROSS JOIN minmax m
            CROSS JOIN corr_data c
        """
        params = {
            "exchange": exchange,
            "symbol0": symbol0,
            "symbol1": symbol1,
            "days": days,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        print(">>>>>>>", exchange, symbol0, symbol1, days, row)
        if row is None:
            return PoolVolumeHistorySummaryPremium(
                price_volatility_pct=None,
                correlation=None,
                geometric_mean_price=None,
            )
        return map_row_to_pool_volume_history_summary_premium(row)
