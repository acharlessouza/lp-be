from __future__ import annotations

from typing import Protocol

from app.domain.entities.pool import Pool


class AllocationPoolPort(Protocol):
    def get_by_address(self, *, pool_address: str, chain_id: int, dex_id: int) -> Pool | None:
        ...
