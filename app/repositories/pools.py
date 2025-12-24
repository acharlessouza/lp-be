from __future__ import annotations

from sqlalchemy import select

from ..models.pool import Pool


class PoolRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def get_by_address(self, pool_address: str, network: str | None = None) -> list[Pool]:
        stmt = select(Pool).where(Pool.pool_address == pool_address.lower())
        if network:
            stmt = stmt.where(Pool.network == network.lower())
        with self._session_factory() as session:
            return list(session.execute(stmt).scalars())
