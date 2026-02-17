from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.domain.entities.catalog import Exchange, Network, PoolDetail, PoolSummary, Token


def map_row_to_exchange(row: Mapping[str, Any]) -> Exchange:
    return Exchange(id=row["id"], name=row["name"])


def map_row_to_network(row: Mapping[str, Any]) -> Network:
    return Network(id=row["id"], name=row["name"])


def map_row_to_token(row: Mapping[str, Any]) -> Token:
    return Token(address=row["address"], symbol=row["symbol"], decimals=row["decimals"])


def map_row_to_pool_summary(row: Mapping[str, Any]) -> PoolSummary:
    return PoolSummary(pool_address=row["pool_address"], fee_tier=row["fee_tier"])


def map_row_to_pool_detail(row: Mapping[str, Any]) -> PoolDetail:
    return PoolDetail(
        id=row["id"],
        dex_key=row["dex_key"],
        dex_name=row["dex_name"],
        dex_version=row["dex_version"],
        chain_key=row["chain_key"],
        chain_name=row["chain_name"],
        fee_tier=row["fee_tier"],
        token0_address=row["token0_address"],
        token0_symbol=row["token0_symbol"],
        token0_decimals=row["token0_decimals"],
        token1_address=row["token1_address"],
        token1_symbol=row["token1_symbol"],
        token1_decimals=row["token1_decimals"],
    )
