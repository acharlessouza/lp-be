from __future__ import annotations

from app.application.dto.catalog import ListExchangeNetworksInput
from app.application.ports.catalog_query_port import CatalogQueryPort
from app.domain.entities.catalog import Network


class ListExchangeNetworksUseCase:
    def __init__(self, *, catalog_port: CatalogQueryPort):
        self._catalog_port = catalog_port

    def execute(self, command: ListExchangeNetworksInput) -> list[Network]:
        return self._catalog_port.list_networks_by_exchange(exchange_id=command.exchange_id)
