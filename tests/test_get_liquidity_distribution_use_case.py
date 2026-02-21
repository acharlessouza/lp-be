from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.application.dto.liquidity_distribution import GetLiquidityDistributionInput
from app.application.use_cases.get_liquidity_distribution import GetLiquidityDistributionUseCase
from app.domain.entities.liquidity_distribution import LiquidityDistributionPool, TickLiquidity


class FakeDistributionPort:
    def __init__(self, pool: LiquidityDistributionPool, rows: list[TickLiquidity]):
        self._pool = pool
        self._rows = rows

    def get_pool_by_id(self, *, pool_id: int) -> LiquidityDistributionPool | None:
        _ = pool_id
        return self._pool

    def find_pools_by_address(
        self,
        *,
        pool_address: str,
        chain_id: int | None = None,
        dex_id: int | None = None,
    ) -> list[LiquidityDistributionPool]:
        _ = (pool_address, chain_id, dex_id)
        return [self._pool]

    def get_latest_period_start(self, *, pool_id: int) -> datetime | None:
        _ = pool_id
        return datetime(2026, 2, 1, 0, 0, 0)

    def get_ticks_by_period(self, *, pool_id: int, period_start: datetime) -> list[TickLiquidity]:
        _ = (pool_id, period_start)
        return self._rows


def test_swapped_pair_inverts_prices_ticks_current_tick_and_pool_labels():
    pool = LiquidityDistributionPool(
        id=1,
        token0_symbol="WETH",
        token1_symbol="USDC",
        token0_decimals=0,
        token1_decimals=0,
        fee_tier=3000,
        tick_spacing=60,
        pool_tick=0,
        current_tick=0,
        current_price_token1_per_token0=Decimal("1"),
        onchain_liquidity=Decimal("100"),
    )
    rows = [
        TickLiquidity(tick_idx=-1, liquidity_net=Decimal("10")),
        TickLiquidity(tick_idx=1, liquidity_net=Decimal("-10")),
    ]
    use_case = GetLiquidityDistributionUseCase(
        distribution_port=FakeDistributionPort(pool, rows)
    )

    canonical = use_case.execute(
        GetLiquidityDistributionInput(
            pool_id=1,
            chain_id=None,
            dex_id=None,
            snapshot_date=date(2026, 2, 1),
            current_tick=0,
            center_tick=None,
            tick_range=10,
            swapped_pair=False,
        )
    )
    swapped = use_case.execute(
        GetLiquidityDistributionInput(
            pool_id=1,
            chain_id=None,
            dex_id=None,
            snapshot_date=date(2026, 2, 1),
            current_tick=0,
            center_tick=None,
            tick_range=10,
            swapped_pair=True,
        )
    )

    assert swapped.token0 == canonical.token1
    assert swapped.token1 == canonical.token0
    assert swapped.current_tick == -canonical.current_tick

    canonical_by_tick = {item.tick: item for item in canonical.data}
    swapped_ticks = [item.tick for item in swapped.data]
    assert swapped_ticks == sorted(swapped_ticks)

    for item in swapped.data:
        source = canonical_by_tick[-item.tick]
        assert item.liquidity == source.liquidity
        assert item.price == (1.0 / source.price)


def test_range_min_max_do_not_change_distribution_window():
    pool = LiquidityDistributionPool(
        id=1,
        token0_symbol="WETH",
        token1_symbol="USDC",
        token0_decimals=18,
        token1_decimals=6,
        fee_tier=3000,
        tick_spacing=60,
        pool_tick=0,
        current_tick=0,
        current_price_token1_per_token0=Decimal("2000"),
        onchain_liquidity=Decimal("100"),
    )
    rows = [
        TickLiquidity(tick_idx=-120, liquidity_net=Decimal("10")),
        TickLiquidity(tick_idx=-60, liquidity_net=Decimal("10")),
        TickLiquidity(tick_idx=0, liquidity_net=Decimal("10")),
        TickLiquidity(tick_idx=60, liquidity_net=Decimal("-10")),
        TickLiquidity(tick_idx=120, liquidity_net=Decimal("-10")),
    ]
    use_case = GetLiquidityDistributionUseCase(
        distribution_port=FakeDistributionPort(pool, rows)
    )

    baseline = use_case.execute(
        GetLiquidityDistributionInput(
            pool_id=1,
            chain_id=None,
            dex_id=None,
            snapshot_date=date(2026, 2, 1),
            current_tick=0,
            center_tick=None,
            tick_range=120,
            swapped_pair=False,
        )
    )
    with_range = use_case.execute(
        GetLiquidityDistributionInput(
            pool_id=1,
            chain_id=None,
            dex_id=None,
            snapshot_date=date(2026, 2, 1),
            current_tick=0,
            center_tick=None,
            tick_range=120,
            range_min=Decimal("0.0005"),
            range_max=Decimal("0.00051"),
            swapped_pair=True,
        )
    )

    # swapped_pair only changes orientation, not the amount of points selected.
    assert len(with_range.data) == len(baseline.data)
