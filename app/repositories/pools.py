from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text


@dataclass(frozen=True)
class PoolRow:
    id: int
    network: str
    pool_address: str
    fee_tier: int
    token0_address: str
    token0_symbol: str
    token1_address: str
    token1_symbol: str


class PoolRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_by_address(self, pool_address: str, network: str | None = None) -> list[PoolRow]:
        sql = """
            SELECT
                id,
                network,
                pool_address,
                fee_tier,
                token0_address,
                token0_symbol,
                token1_address,
                token1_symbol
            FROM pools
            WHERE pool_address = :pool_address
        """
        params = {"pool_address": pool_address.lower()}
        if network:
            sql += " AND network = :network"
            params["network"] = network.lower()

        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        return [
            PoolRow(
                id=row["id"],
                network=row["network"],
                pool_address=row["pool_address"],
                fee_tier=row["fee_tier"],
                token0_address=row["token0_address"],
                token0_symbol=row["token0_symbol"],
                token1_address=row["token1_address"],
                token1_symbol=row["token1_symbol"],
            )
            for row in rows
        ]

    def get_by_id(self, pool_id: int) -> PoolRow | None:
        sql = """
            SELECT
                id,
                network,
                pool_address,
                fee_tier,
                token0_address,
                token0_symbol,
                token1_address,
                token1_symbol
            FROM pools
            WHERE id = :pool_id
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"pool_id": pool_id}).mappings().first()
        if not row:
            return None
        return PoolRow(
            id=row["id"],
            network=row["network"],
            pool_address=row["pool_address"],
            fee_tier=row["fee_tier"],
            token0_address=row["token0_address"],
            token0_symbol=row["token0_symbol"],
            token1_address=row["token1_address"],
            token1_symbol=row["token1_symbol"],
        )
