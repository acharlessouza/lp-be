from __future__ import annotations

from typing import Protocol

from app.domain.entities.match_ticks import MatchTicksLatestPrices, MatchTicksPoolConfig


class MatchTicksPort(Protocol):
    def get_pool_config(self, *, pool_id: int) -> MatchTicksPoolConfig | None:
        ...

    def get_latest_prices(self, *, pool_id: int) -> MatchTicksLatestPrices | None:
        ...
