from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import httpx


class PriceLookupError(RuntimeError):
    pass


def _normalize_token_key(value: str) -> str:
    return value.strip().lower()


def _normalize_network(value: str) -> str:
    return value.strip().lower()


COINGECKO_PLATFORMS = {
    "ethereum": "ethereum",
    "mainnet": "ethereum",
    "eth": "ethereum",
    "polygon": "polygon-pos",
    "matic": "polygon-pos",
    "arbitrum": "arbitrum-one",
    "arbitrum-one": "arbitrum-one",
    "base": "base",
}


@dataclass(frozen=True)
class PriceOverrides:
    data: dict

    def get_price(self, network: str, token: str) -> Decimal | None:
        network_key = _normalize_network(network)
        token_key = _normalize_token_key(token)
        for key in (network_key, "default"):
            bucket = self.data.get(key) if isinstance(self.data, dict) else None
            if not isinstance(bucket, dict):
                continue
            value = bucket.get(token) or bucket.get(token_key)
            if value is None:
                continue
            return Decimal(str(value))
        return None


class CoingeckoPriceProvider:
    def __init__(self, api_base: str, timeout_seconds: float):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout_seconds

    def get_price_usd(self, network: str, token_address: str) -> Decimal:
        platform = COINGECKO_PLATFORMS.get(_normalize_network(network))
        if not platform:
            raise PriceLookupError(f"Unsupported network for pricing: {network}")
        if not token_address.lower().startswith("0x"):
            raise PriceLookupError("Coingecko pricing requires a token address.")

        url = f"{self.api_base}/simple/token_price/{platform}"
        params = {
            "contract_addresses": token_address,
            "vs_currencies": "usd",
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        token_key = token_address.lower()
        if token_key not in payload or "usd" not in payload[token_key]:
            raise PriceLookupError("Price not found for token.")
        return Decimal(str(payload[token_key]["usd"]))


class PriceService:
    def __init__(self, overrides: PriceOverrides, coingecko: CoingeckoPriceProvider):
        self.overrides = overrides
        self.coingecko = coingecko

    def get_price_usd(self, *, token: str, network: str) -> Decimal:
        override = self.overrides.get_price(network, token)
        if override is not None:
            return override
        if token.lower().startswith("0x"):
            return self.coingecko.get_price_usd(network, token)
        raise PriceLookupError(
            "Token price unavailable. Provide PRICE_OVERRIDES or use token address."
        )

    def get_pair_prices(self, *, token0: str, token1: str, network: str) -> tuple[Decimal, Decimal]:
        price0 = self.get_price_usd(token=token0, network=network)
        price1 = self.get_price_usd(token=token1, network=network)
        return price0, price1
