from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.entities.discover_pools import DiscoverPoolAggregate


class DiscoverPoolsPort(Protocol):
    def list_pools(
        self,
        *,
        start_dt: datetime,
        network_id: int | None,
        exchange_id: int | None,
        token_symbol: str | None,
    ) -> list[DiscoverPoolAggregate]:
        ...
