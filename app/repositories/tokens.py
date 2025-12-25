from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text


@dataclass(frozen=True)
class TokenRow:
    address: str
    symbol: str
    decimals: int


class TokenRepository:
    def __init__(self, engine):
        self._engine = engine

    def list_by_exchange_network(
        self,
        *,
        exchange_id: int,
        network_id: int,
        token_address: str | None = None,
    ) -> list[TokenRow]:
        sql = """
            SELECT DISTINCT
                token_address AS address,
                token_symbol AS symbol,
                token_decimals AS decimals
            FROM (
                SELECT
                    token0_address AS token_address,
                    token0_symbol AS token_symbol,
                    token0_decimals AS token_decimals
                FROM pools p
                WHERE p.exchange_id = :exchange_id
                  AND p.network_id = :network_id
                  AND (:token IS NULL OR p.token0_address = :token OR p.token1_address = :token)
                  AND EXISTS (
                    SELECT 1
                    FROM pool_days pd
                    WHERE pd.pool_id = p.id
                      AND pd.date >= CURRENT_DATE - INTERVAL '90 days'
                  )
                UNION
                SELECT
                    token1_address AS token_address,
                    token1_symbol AS token_symbol,
                    token1_decimals AS token_decimals
                FROM pools p
                WHERE p.exchange_id = :exchange_id
                  AND p.network_id = :network_id
                  AND (:token IS NULL OR p.token0_address = :token OR p.token1_address = :token)
                  AND EXISTS (
                    SELECT 1
                    FROM pool_days pd
                    WHERE pd.pool_id = p.id
                      AND pd.date >= CURRENT_DATE - INTERVAL '90 days'
                  )
            ) tokens
            WHERE (:token IS NULL OR token_address <> :token)
            ORDER BY symbol
        """
        params = {
            "exchange_id": exchange_id,
            "network_id": network_id,
            "token": token_address.lower() if token_address else None,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()

        return [
            TokenRow(address=row["address"], symbol=row["symbol"], decimals=row["decimals"])
            for row in rows
        ]
