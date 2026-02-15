from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal

from dotenv import load_dotenv


load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def _json(name: str) -> dict:
    value = _env(name)
    if not value:
        return {}
    return json.loads(value)


@dataclass(frozen=True)
class Settings:
    price_overrides: dict
    coingecko_api_base: str
    coingecko_timeout_seconds: float
    postgres_dsn: str
    graph_api_key: str
    graph_gateway_base: str
    graph_subgraph_ids: dict
    graph_request_timeout_seconds: float
    pool_min_tvl_usd: Decimal


def get_settings() -> Settings:
    subgraphs = {
        "ethereum": _env("GRAPH_SUBGRAPH_ID_ETHEREUM", ""),
        "arbitrum": _env("GRAPH_SUBGRAPH_ID_ARBITRUM", ""),
        "base": _env("GRAPH_SUBGRAPH_ID_BASE", ""),
        "polygon": _env("GRAPH_SUBGRAPH_ID_POLYGON", ""),
        "bsc": _env("GRAPH_SUBGRAPH_ID_BSC", ""),
    }
    return Settings(
        price_overrides=_json("PRICE_OVERRIDES"),
        coingecko_api_base=_env("COINGECKO_API_BASE", "https://api.coingecko.com/api/v3"),
        coingecko_timeout_seconds=float(_env("COINGECKO_TIMEOUT_SECONDS", "10")),
        postgres_dsn=_env("POSTGRES_DSN", ""),
        graph_api_key=_env("GRAPH_API_KEY", ""),
        graph_gateway_base=_env("GRAPH_GATEWAY_BASE", "https://gateway.thegraph.com/api"),
        graph_subgraph_ids=subgraphs,
        graph_request_timeout_seconds=float(_env("GRAPH_REQUEST_TIMEOUT_SECONDS", "10")),
        pool_min_tvl_usd=Decimal(_env("POOL_MIN_TVL_USD", "100000")),
    )
