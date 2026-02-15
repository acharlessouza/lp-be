from __future__ import annotations

from typing import Protocol

from app.domain.entities.catalog import Exchange, Network, PoolDetail, PoolSummary, Token


class CatalogQueryPort(Protocol):
    def list_exchanges(self) -> list[Exchange]:
        ...

    def list_networks_by_exchange(self, *, exchange_id: int) -> list[Network]:
        ...

    def list_tokens_by_exchange_network(
        self,
        *,
        exchange_id: int,
        network_id: int,
        token_address: str | None = None,
    ) -> list[Token]:
        ...

    def list_pools_by_exchange_network_tokens(
        self,
        *,
        exchange_id: int,
        network_id: int,
        token0_address: str,
        token1_address: str,
    ) -> list[PoolSummary]:
        ...

    def get_pool_by_address(
        self,
        *,
        pool_address: str,
        network: str,
        exchange_id: int,
    ) -> PoolDetail | None:
        ...
