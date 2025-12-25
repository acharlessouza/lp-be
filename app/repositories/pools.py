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
    token0_decimals: int
    token1_address: str
    token1_symbol: str
    token1_decimals: int


@dataclass(frozen=True)
class PoolSummaryRow:
    pool_address: str
    fee_tier: int


class PoolRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_by_address(
        self,
        pool_address: str,
        network: str | None = None,
        exchange_id: int | None = None,
    ) -> list[PoolRow]:
        sql = """
            SELECT
                p.id,
                n.name AS network,
                p.pool_address,
                p.fee_tier,
                p.token0_address,
                p.token0_symbol,
                p.token0_decimals,
                p.token1_address,
                p.token1_symbol,
                p.token1_decimals
            FROM pools p
            JOIN networks n ON n.id = p.network_id
            WHERE p.pool_address = :pool_address
        """
        params = {"pool_address": pool_address.lower()}
        if network:
            sql += " AND n.name = :network"
            params["network"] = network.lower()
        if exchange_id is not None:
            sql += " AND p.exchange_id = :exchange_id"
            params["exchange_id"] = exchange_id
        sql += " ORDER BY p.id"

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
                token0_decimals=row["token0_decimals"],
                token1_address=row["token1_address"],
                token1_symbol=row["token1_symbol"],
                token1_decimals=row["token1_decimals"],
            )
            for row in rows
        ]

    def get_by_id(self, pool_id: int) -> PoolRow | None:
        sql = """
            SELECT
                p.id,
                n.name AS network,
                p.pool_address,
                p.fee_tier,
                p.token0_address,
                p.token0_symbol,
                p.token0_decimals,
                p.token1_address,
                p.token1_symbol,
                p.token1_decimals
            FROM pools p
            JOIN networks n ON n.id = p.network_id
            WHERE p.id = :pool_id
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
            token0_decimals=row["token0_decimals"],
            token1_address=row["token1_address"],
            token1_symbol=row["token1_symbol"],
            token1_decimals=row["token1_decimals"],
        )

    def list_by_exchange_network_tokens(
        self,
        *,
        exchange_id: int,
        network_id: int,
        token0_address: str,
        token1_address: str,
    ) -> list[PoolSummaryRow]:
        sql = """
            SELECT
                p.pool_address,
                p.fee_tier
            FROM pools p
            WHERE p.exchange_id = :exchange_id
              AND p.network_id = :network_id
              AND (
                    (p.token0_address = :token0_address AND p.token1_address = :token1_address)
                 OR (p.token0_address = :token1_address AND p.token1_address = :token0_address)
              )
            
            ORDER BY p.fee_tier, p.pool_address;


        """
        params = {
            "exchange_id": exchange_id,
            "network_id": network_id,
            "token0_address": token0_address.lower(),
            "token1_address": token1_address.lower(),
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        return [
            PoolSummaryRow(
                pool_address=row["pool_address"],
                fee_tier=row["fee_tier"],
            )
            for row in rows
        ]
