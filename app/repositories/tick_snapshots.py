from __future__ import annotations

from datetime import date

from sqlalchemy import text


class TickSnapshotRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_latest_date(self, pool_id: int) -> date | None:
        sql = "SELECT max(date) AS latest_date FROM tick_snapshots WHERE pool_id = :pool_id"
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        return row["latest_date"] if row else None

    def get_ticks_for_date(self, pool_id: int, snapshot_date: date) -> list[tuple]:
        sql = """
            SELECT tick_idx, price0, price1, liquidity_net
            FROM tick_snapshots
            WHERE pool_id = :pool_id AND date = :snapshot_date
            ORDER BY tick_idx ASC
        """
        with self._engine.connect() as conn:
            return list(
                conn.execute(
                    text(sql),
                    {"pool_id": pool_id, "snapshot_date": snapshot_date},
                ).all()
            )
