from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

from sqlalchemy import text


@dataclass(frozen=True)
class DiscoverPoolRow:
    pool_id: int
    pool_address: str
    network_name: str
    exchange_name: str
    token0_symbol: str
    token1_symbol: str
    fee_tier: int
    avg_tvl_usd: Decimal | None
    total_fees_usd: Decimal | None
    avg_hourly_fees_usd: Decimal | None
    avg_hourly_volume_usd: Decimal | None
    samples: int


class DiscoverPoolsRepository:
    def __init__(self, engine):
        self._engine = engine

    def list_pools(
        self,
        *,
        start_dt: datetime,
        network_id: int | None,
        exchange_id: int | None,
        token_symbol: str | None,
    ) -> list[DiscoverPoolRow]:
        sql = """
            SELECT
                p.id AS pool_id,
                p.pool_address,
                n.name AS network_name,
                e.name AS exchange_name,
                p.token0_symbol,
                p.token1_symbol,
                p.fee_tier,
                AVG(ph.tvl_usd) AS avg_tvl_usd,
                SUM(ph.fees_usd) AS total_fees_usd,
                AVG(ph.fees_usd) AS avg_hourly_fees_usd,
                AVG(ph.volume_usd) AS avg_hourly_volume_usd,
                COUNT(*) AS samples
            FROM pools p
            JOIN pool_hours ph ON ph.pool_id = p.id
            JOIN networks n ON n.id = p.network_id
            JOIN exchanges e ON e.id = p.exchange_id
            WHERE ph.period_start >= :start_dt
              AND (:network_id IS NULL OR p.network_id = :network_id)
              AND (:exchange_id IS NULL OR p.exchange_id = :exchange_id)
              AND (
                :token_symbol IS NULL
                OR UPPER(p.token0_symbol) = :token_symbol
                OR UPPER(p.token1_symbol) = :token_symbol
              )
            GROUP BY
                p.id,
                p.pool_address,
                n.name,
                e.name,
                p.token0_symbol,
                p.token1_symbol,
                p.fee_tier
        """
        params = {
            "start_dt": start_dt,
            "network_id": network_id,
            "exchange_id": exchange_id,
            "token_symbol": token_symbol,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        return [
            DiscoverPoolRow(
                pool_id=row["pool_id"],
                pool_address=row["pool_address"],
                network_name=row["network_name"],
                exchange_name=row["exchange_name"],
                token0_symbol=row["token0_symbol"],
                token1_symbol=row["token1_symbol"],
                fee_tier=row["fee_tier"],
                avg_tvl_usd=Decimal(str(row["avg_tvl_usd"])) if row["avg_tvl_usd"] is not None else None,
                total_fees_usd=Decimal(str(row["total_fees_usd"]))
                if row["total_fees_usd"] is not None
                else None,
                avg_hourly_fees_usd=Decimal(str(row["avg_hourly_fees_usd"]))
                if row["avg_hourly_fees_usd"] is not None
                else None,
                avg_hourly_volume_usd=Decimal(str(row["avg_hourly_volume_usd"]))
                if row["avg_hourly_volume_usd"] is not None
                else None,
                samples=int(row["samples"] or 0),
            )
            for row in rows
        ]
