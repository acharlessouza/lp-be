from __future__ import annotations

from app.application.dto.catalog import ListExchangeNetworkTokensInput
from app.application.ports.catalog_query_port import CatalogQueryPort
from app.domain.entities.catalog import Token


class ListExchangeNetworkTokensUseCase:
    def __init__(self, *, catalog_port: CatalogQueryPort):
        self._catalog_port = catalog_port

    def execute(self, command: ListExchangeNetworkTokensInput) -> list[Token]:
        return self._catalog_port.list_tokens_by_exchange_network(
            exchange_id=command.exchange_id,
            network_id=command.network_id,
            token_address=command.token_address,
        )
