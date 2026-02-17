from __future__ import annotations

from app.application.dto.catalog import GetPoolByAddressInput
from app.application.ports.catalog_query_port import CatalogQueryPort
from app.domain.entities.catalog import PoolDetail
from app.domain.exceptions import PoolNotFoundError


class GetPoolByAddressUseCase:
    def __init__(self, *, catalog_port: CatalogQueryPort):
        self._catalog_port = catalog_port

    def execute(self, command: GetPoolByAddressInput) -> PoolDetail:
        pool = self._catalog_port.get_pool_by_address(
            pool_address=command.pool_address,
            chain_id=command.chain_id,
            exchange_id=command.exchange_id,
        )
        if pool is None:
            raise PoolNotFoundError("Pool not found.")
        return pool
