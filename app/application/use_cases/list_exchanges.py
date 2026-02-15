from __future__ import annotations

from app.application.ports.catalog_query_port import CatalogQueryPort
from app.domain.entities.catalog import Exchange


class ListExchangesUseCase:
    def __init__(self, *, catalog_port: CatalogQueryPort):
        self._catalog_port = catalog_port

    def execute(self) -> list[Exchange]:
        return self._catalog_port.list_exchanges()
