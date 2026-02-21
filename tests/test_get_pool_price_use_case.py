from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.application.dto.pool_price import GetPoolPriceInput
from app.application.use_cases.get_pool_price import GetPoolPriceUseCase
from app.domain.entities.pool_price import PoolCurrentPrice, PoolPricePoint, PoolPriceStats
from app.domain.exceptions import PoolPriceInputError


class FakePoolPricePort:
    def __init__(
        self,
        *,
        stats: PoolPriceStats,
        series: list[PoolPricePoint],
        current: PoolCurrentPrice,
    ):
        self._stats = stats
        self._series = series
        self._current = current

    def pool_exists(self, *, pool_address: str, chain_id: int, dex_id: int) -> bool:
        _ = (pool_address, chain_id, dex_id)
        return True

    def get_series(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        days: int,
    ) -> list[PoolPricePoint]:
        _ = (pool_address, chain_id, dex_id, days)
        return self._series

    def get_series_range(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        start: datetime,
        end: datetime,
    ) -> list[PoolPricePoint]:
        _ = (pool_address, chain_id, dex_id, start, end)
        return self._series

    def get_stats(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        days: int,
    ) -> PoolPriceStats:
        _ = (pool_address, chain_id, dex_id, days)
        return self._stats

    def get_stats_range(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        start: datetime,
        end: datetime,
    ) -> PoolPriceStats:
        _ = (pool_address, chain_id, dex_id, start, end)
        return self._stats

    def get_latest_price(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> PoolCurrentPrice | None:
        _ = (pool_address, chain_id, dex_id)
        return self._current


def test_swapped_pair_inverts_series_and_recomputes_stats():
    use_case = GetPoolPriceUseCase(
        pool_price_port=FakePoolPricePort(
            stats=PoolPriceStats(
                min_price=Decimal("1"),
                max_price=Decimal("9"),
                avg_price=Decimal("5"),
            ),
            series=[
                PoolPricePoint(timestamp=datetime(2026, 1, 1, 0, 0, 0), price=Decimal("2")),
                PoolPricePoint(timestamp=datetime(2026, 1, 1, 1, 0, 0), price=Decimal("4")),
            ],
            current=PoolCurrentPrice(
                token1_price=Decimal("8"),
                token0_price=None,
                sqrt_price_x96=None,
            ),
        )
    )

    result = use_case.execute(
        GetPoolPriceInput(
            pool_address="0xpool",
            chain_id=1,
            dex_id=2,
            days=7,
            swapped_pair=True,
        )
    )

    assert [row.price for row in result.series] == [Decimal("0.5"), Decimal("0.25")]
    assert result.min_price == Decimal("0.25")
    assert result.max_price == Decimal("0.5")
    assert result.avg_price == Decimal("0.375")
    assert result.current_price == Decimal("0.125")


def test_swapped_pair_rejects_zero_price_in_series():
    use_case = GetPoolPriceUseCase(
        pool_price_port=FakePoolPricePort(
            stats=PoolPriceStats(min_price=None, max_price=None, avg_price=None),
            series=[
                PoolPricePoint(timestamp=datetime(2026, 1, 1, 0, 0, 0), price=Decimal("0")),
            ],
            current=PoolCurrentPrice(
                token1_price=Decimal("1"),
                token0_price=None,
                sqrt_price_x96=None,
            ),
        )
    )

    with pytest.raises(PoolPriceInputError):
        use_case.execute(
            GetPoolPriceInput(
                pool_address="0xpool",
                chain_id=1,
                dex_id=2,
                days=7,
                swapped_pair=True,
            )
        )
