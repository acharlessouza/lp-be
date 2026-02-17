from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListExchangeNetworksInput:
    exchange_id: int


@dataclass(frozen=True)
class ListExchangeNetworkTokensInput:
    exchange_id: int
    network_id: int
    token_address: str | None = None


@dataclass(frozen=True)
class ListExchangeNetworkPoolsInput:
    exchange_id: int
    network_id: int
    token0_address: str
    token1_address: str


@dataclass(frozen=True)
class GetPoolByAddressInput:
    pool_address: str
    chain_id: int
    exchange_id: int
