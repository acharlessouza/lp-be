from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text


@dataclass(frozen=True)
class PoolCurrentPriceRow:
    token1_price: Decimal | None
    token0_price: Decimal | None
    sqrt_price_x96: int | None


class CurrentPriceRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_latest_price(self, *, pool_id: int) -> PoolCurrentPriceRow | None:
        sql = """
            SELECT
                token1_price,
                token0_price,
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
        token1_price = row["token1_price"]
        token0_price = row["token0_price"]
        sqrt_price_x96 = row["sqrt_price_x96"]
        return PoolCurrentPriceRow(
            token1_price=Decimal(str(token1_price)) if token1_price is not None else None,
            token0_price=Decimal(str(token0_price)) if token0_price is not None else None,
            sqrt_price_x96=int(sqrt_price_x96) if sqrt_price_x96 is not None else None,
        )
