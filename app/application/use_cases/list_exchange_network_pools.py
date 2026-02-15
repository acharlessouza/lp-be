from __future__ import annotations

from app.application.dto.catalog import ListExchangeNetworkPoolsInput
from app.application.ports.catalog_query_port import CatalogQueryPort
from app.domain.entities.catalog import PoolSummary


class ListExchangeNetworkPoolsUseCase:
    def __init__(self, *, catalog_port: CatalogQueryPort):
        self._catalog_port = catalog_port

    def execute(self, command: ListExchangeNetworkPoolsInput) -> list[PoolSummary]:
        return self._catalog_port.list_pools_by_exchange_network_tokens(
            exchange_id=command.exchange_id,
            network_id=command.network_id,
            token0_address=command.token0_address,
            token1_address=command.token1_address,
        )
