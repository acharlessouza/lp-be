from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from app.application.ports.catalog_query_port import CatalogQueryPort
from app.domain.entities.catalog import Exchange, Network, PoolDetail, PoolSummary, Token
from app.infrastructure.db.mappers.catalog_mapper import (
    map_row_to_exchange,
    map_row_to_network,
    map_row_to_pool_detail,
    map_row_to_pool_summary,
    map_row_to_token,
)


class SqlCatalogQueryRepository(CatalogQueryPort):
    def __init__(self, engine, min_tvl_usd: Decimal):
        self._engine = engine
        self._min_tvl_usd = min_tvl_usd

    def list_exchanges(self) -> list[Exchange]:
        sql = """
            SELECT DISTINCT
                d.dex_id AS id,
                d.name
            FROM public.dexes d
            JOIN public.pools p
              ON p.dex_id = d.dex_id
            WHERE COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
            ORDER BY d.name
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), {"min_tvl_usd": self._min_tvl_usd}).mappings().all()
        return [map_row_to_exchange(row) for row in rows]

    def list_networks_by_exchange(self, *, exchange_id: int) -> list[Network]:
        sql = """
            SELECT DISTINCT
                c.chain_id AS id,
                c.name
            FROM public.chains c
            JOIN public.pools p
              ON p.chain_id = c.chain_id
            WHERE p.dex_id = :exchange_id
              AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
            ORDER BY c.name
        """
        params = {
            "exchange_id": exchange_id,
            "min_tvl_usd": self._min_tvl_usd,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [map_row_to_network(row) for row in rows]

    def list_tokens_by_exchange_network(
        self,
        *,
        exchange_id: int,
        network_id: int,
        token_address: str | None = None,
    ) -> list[Token]:
        sql = """
            SELECT DISTINCT
                token_address AS address,
                COALESCE(t.symbol, token_address) AS symbol,
                COALESCE(t.decimals, 0) AS decimals
            FROM (
                SELECT
                    p.token0_address AS token_address
                FROM public.pools p
                WHERE p.dex_id = :exchange_id
                  AND p.chain_id = :network_id
                  AND (:token IS NULL OR lower(p.token0_address) = :token OR lower(p.token1_address) = :token)
                  AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
                UNION
                SELECT
                    p.token1_address AS token_address
                FROM public.pools p
                WHERE p.dex_id = :exchange_id
                  AND p.chain_id = :network_id
                  AND (:token IS NULL OR lower(p.token0_address) = :token OR lower(p.token1_address) = :token)
                  AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
            ) tokens
            LEFT JOIN public.tokens t
              ON t.chain_id = :network_id
             AND lower(t.address) = lower(tokens.token_address)
            WHERE (:token IS NULL OR lower(token_address) <> :token)
            ORDER BY symbol
        """
        params = {
            "exchange_id": exchange_id,
            "network_id": network_id,
            "token": token_address.lower() if token_address else None,
            "min_tvl_usd": self._min_tvl_usd,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [map_row_to_token(row) for row in rows]

    def list_pools_by_exchange_network_tokens(
        self,
        *,
        exchange_id: int,
        network_id: int,
        token0_address: str,
        token1_address: str,
    ) -> list[PoolSummary]:
        sql = """
            SELECT
                p.pool_address,
                COALESCE(p.fee_tier, 0) AS fee_tier
            FROM public.pools p
            WHERE p.dex_id = :exchange_id
              AND p.chain_id = :network_id
              AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
              AND (
                (lower(p.token0_address) = :token0_address AND lower(p.token1_address) = :token1_address)
                OR (lower(p.token0_address) = :token1_address AND lower(p.token1_address) = :token0_address)
              )
            ORDER BY COALESCE(p.fee_tier, 0), p.pool_address
        """
        params = {
            "exchange_id": exchange_id,
            "network_id": network_id,
            "token0_address": token0_address.lower(),
            "token1_address": token1_address.lower(),
            "min_tvl_usd": self._min_tvl_usd,
        }
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().all()
        return [map_row_to_pool_summary(row) for row in rows]

    def get_pool_by_address(
        self,
        *,
        pool_address: str,
        chain_id: int,
        exchange_id: int,
    ) -> PoolDetail | None:
        sql = """
            SELECT
                p.pool_address AS id,
                d.dex_key,
                d.name AS dex_name,
                CAST(d.version AS text) AS dex_version,
                c.chain_key,
                c.name AS chain_name,
                COALESCE(p.fee_tier, 0) AS fee_tier,
                p.token0_address,
                COALESCE(t0.symbol, p.token0_address) AS token0_symbol,
                COALESCE(t0.decimals, 0) AS token0_decimals,
                p.token1_address,
                COALESCE(t1.symbol, p.token1_address) AS token1_symbol,
                COALESCE(t1.decimals, 0) AS token1_decimals
            FROM public.pools p
            JOIN public.dexes d
              ON d.dex_id = p.dex_id
            JOIN public.chains c
              ON c.chain_id = p.chain_id
            LEFT JOIN public.tokens t0
              ON t0.chain_id = p.chain_id
             AND lower(t0.address) = lower(p.token0_address)
            LEFT JOIN public.tokens t1
              ON t1.chain_id = p.chain_id
             AND lower(t1.address) = lower(p.token1_address)
            WHERE lower(p.pool_address) = :pool_address
              AND p.chain_id = :chain_id
              AND p.dex_id = :exchange_id
              AND COALESCE(p.tvl_usd, 0) >= :min_tvl_usd
            ORDER BY p.dex_id, p.chain_id, p.pool_address
            LIMIT 1
        """
        params = {
            "pool_address": pool_address.lower(),
            "chain_id": chain_id,
            "exchange_id": exchange_id,
            "min_tvl_usd": self._min_tvl_usd,
        }
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().first()
        if not row:
            return None
        return map_row_to_pool_detail(row)
