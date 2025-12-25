from __future__ import annotations

from sqlalchemy import text


class CurrentTickRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_latest_sqrt_price_x96(self, *, pool_id: int) -> int | None:
        sql = """
            SELECT
                sqrt_price_x96
            FROM pool_hours
            WHERE pool_id = :pool_id
            ORDER BY period_start DESC
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        value = row["sqrt_price_x96"]
        if value is None:
            return None
        return int(value)
