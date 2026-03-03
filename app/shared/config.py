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


def _bool(name: str, default: bool) -> bool:
    raw = _env(name, "true" if default else "false")
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str = "") -> list[str]:
    raw = _env(name, default) or default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    price_overrides: dict
    coingecko_api_base: str
    coingecko_timeout_seconds: float
    coingecko_cache_ttl_seconds: float
    postgres_dsn: str
    graph_api_key: str
    graph_gateway_base: str
    graph_subgraph_ids: dict
    graph_blocks_subgraph_ids: dict
    graph_request_timeout_seconds: float
    graph_on_demand_timeout_seconds: float
    graph_on_demand_max_retries: int
    graph_on_demand_min_interval_ms: int
    graph_on_demand_max_combinations: int
    pool_min_tvl_usd: Decimal
    jwt_secret: str
    jwt_access_ttl_minutes: int
    jwt_refresh_ttl_days: int
    google_client_id: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_success_url: str
    stripe_cancel_url: str
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    auth_cookie_domain: str | None
    frontend_base_url: str
    email_sender_mode: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    smtp_from: str
    cors_allow_origins: list[str]


def get_settings() -> Settings:
    subgraphs = {
        "ethereum": _env("GRAPH_SUBGRAPH_ID_ETHEREUM", ""),
        "arbitrum": _env("GRAPH_SUBGRAPH_ID_ARBITRUM", ""),
        "base": _env("GRAPH_SUBGRAPH_ID_BASE", ""),
        "polygon": _env("GRAPH_SUBGRAPH_ID_POLYGON", ""),
        "bsc": _env("GRAPH_SUBGRAPH_ID_BSC", ""),
    }
    block_subgraphs = {
        "ethereum": _env("GRAPH_BLOCKS_SUBGRAPH_ID_ETHEREUM", ""),
        "arbitrum": _env("GRAPH_BLOCKS_SUBGRAPH_ID_ARBITRUM", ""),
        "base": _env("GRAPH_BLOCKS_SUBGRAPH_ID_BASE", ""),
        "polygon": _env("GRAPH_BLOCKS_SUBGRAPH_ID_POLYGON", ""),
        "bsc": _env("GRAPH_BLOCKS_SUBGRAPH_ID_BSC", ""),
    }
    return Settings(
        price_overrides=_json("PRICE_OVERRIDES"),
        coingecko_api_base=_env("COINGECKO_API_BASE", "https://api.coingecko.com/api/v3"),
        coingecko_timeout_seconds=float(_env("COINGECKO_TIMEOUT_SECONDS", "10")),
        coingecko_cache_ttl_seconds=float(_env("COINGECKO_CACHE_TTL_SECONDS", "300")),
        postgres_dsn=_env("POSTGRES_DSN", ""),
        graph_api_key=_env("GRAPH_API_KEY", ""),
        graph_gateway_base=_env("GRAPH_GATEWAY_BASE", "https://gateway.thegraph.com/api"),
        graph_subgraph_ids=subgraphs,
        graph_blocks_subgraph_ids=block_subgraphs,
        graph_request_timeout_seconds=float(_env("GRAPH_REQUEST_TIMEOUT_SECONDS", "10")),
        graph_on_demand_timeout_seconds=float(_env("GRAPH_ON_DEMAND_TIMEOUT_SECONDS", "15")),
        graph_on_demand_max_retries=int(_env("GRAPH_ON_DEMAND_MAX_RETRIES", "3")),
        graph_on_demand_min_interval_ms=int(_env("GRAPH_ON_DEMAND_MIN_INTERVAL_MS", "120")),
        graph_on_demand_max_combinations=int(_env("GRAPH_ON_DEMAND_MAX_COMBINATIONS", "4")),
        pool_min_tvl_usd=Decimal(_env("POOL_MIN_TVL_USD", "100000")),
        jwt_secret=_env("JWT_SECRET", "") or "",
        jwt_access_ttl_minutes=int(_env("JWT_ACCESS_TTL_MINUTES", "15")),
        jwt_refresh_ttl_days=int(_env("JWT_REFRESH_TTL_DAYS", "30")),
        google_client_id=_env("GOOGLE_CLIENT_ID", "") or "",
        stripe_secret_key=_env("STRIPE_SECRET_KEY", "") or "",
        stripe_webhook_secret=_env("STRIPE_WEBHOOK_SECRET", "") or "",
        stripe_success_url=_env("STRIPE_SUCCESS_URL", "") or "",
        stripe_cancel_url=_env("STRIPE_CANCEL_URL", "") or "",
        auth_cookie_secure=_bool("AUTH_COOKIE_SECURE", False),
        auth_cookie_samesite=(_env("AUTH_COOKIE_SAMESITE", "lax") or "lax").lower(),
        auth_cookie_domain=_env("AUTH_COOKIE_DOMAIN"),
        frontend_base_url=_env("FRONTEND_BASE_URL", "") or "",
        email_sender_mode=(_env("EMAIL_SENDER_MODE", "console") or "console").lower(),
        smtp_host=_env("SMTP_HOST", "") or "",
        smtp_port=int(_env("SMTP_PORT", "587")),
        smtp_user=_env("SMTP_USER", "") or "",
        smtp_pass=_env("SMTP_PASS", "") or "",
        smtp_from=_env("SMTP_FROM", "") or "",
        cors_allow_origins=_csv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:5173,http://localhost:3000",
        ),
    )
