from __future__ import annotations

import json
import os
from dataclasses import dataclass

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


def get_settings() -> Settings:
    return Settings(
        price_overrides=_json("PRICE_OVERRIDES"),
        coingecko_api_base=_env("COINGECKO_API_BASE", "https://api.coingecko.com/api/v3"),
        coingecko_timeout_seconds=float(_env("COINGECKO_TIMEOUT_SECONDS", "10")),
        postgres_dsn=_env("POSTGRES_DSN", ""),
    )
