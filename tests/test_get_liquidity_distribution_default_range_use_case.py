from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import unittest

from app.application.dto.liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeInput,
)
from app.application.use_cases.get_liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeUseCase,
)
from app.domain.entities.liquidity_distribution import LiquidityDistributionPool, TickLiquidity
from app.domain.exceptions import LiquidityDistributionInputError


class FakeDistributionPort:
    def __init__(self, pool: LiquidityDistributionPool | None):
        self._pool = pool

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
        return [] if self._pool is None else [self._pool]

    def get_latest_period_start(self, *, pool_id: int) -> datetime | None:
        _ = pool_id
        return None

    def get_ticks_by_period(self, *, pool_id: int, period_start: datetime) -> list[TickLiquidity]:
        _ = (pool_id, period_start)
        return []


class GetLiquidityDistributionDefaultRangeUseCaseTests(unittest.TestCase):
    def test_uses_pool_tick_spacing_and_center_tick(self):
        pool = LiquidityDistributionPool(
            id=1,
            token0_symbol="WETH",
            token1_symbol="USDT",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=None,
            tick_spacing=60,
            pool_tick=100000,
            current_tick=100000,
            current_price_token1_per_token0=Decimal("2000"),
            onchain_liquidity=Decimal("1"),
        )
        use_case = GetLiquidityDistributionDefaultRangeUseCase(
            distribution_port=FakeDistributionPort(pool)
        )

        result = use_case.execute(
            GetLiquidityDistributionDefaultRangeInput(
                pool_id=1,
                chain_id=None,
                dex_id=None,
                snapshot_date=date(2026, 2, 16),
                preset="stable",
                initial_price=None,
                center_tick=12345,
                swapped_pair=False,
            )
        )

        self.assertEqual(result.tick_spacing, 60)
        self.assertEqual(result.min_tick, 12120)
        self.assertEqual(result.max_tick, 12480)
        self.assertLess(result.min_price, result.max_price)

    def test_fallback_to_fee_tier_for_tick_spacing(self):
        pool = LiquidityDistributionPool(
            id=1,
            token0_symbol="WETH",
            token1_symbol="USDT",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=None,
            pool_tick=200000,
            current_tick=200000,
            current_price_token1_per_token0=Decimal("2000"),
            onchain_liquidity=Decimal("1"),
        )
        use_case = GetLiquidityDistributionDefaultRangeUseCase(
            distribution_port=FakeDistributionPort(pool)
        )

        result = use_case.execute(
            GetLiquidityDistributionDefaultRangeInput(
                pool_id=1,
                chain_id=None,
                dex_id=None,
                snapshot_date=date(2026, 2, 16),
                preset="wide",
                initial_price=None,
                center_tick=None,
                swapped_pair=False,
            )
        )

        self.assertEqual(result.tick_spacing, 60)
        self.assertEqual(result.min_tick % 60, 0)
        self.assertEqual(result.max_tick % 60, 0)
        self.assertLess(result.min_price, result.max_price)

    def test_raises_when_tick_spacing_cannot_be_derived(self):
        pool = LiquidityDistributionPool(
            id=1,
            token0_symbol="WETH",
            token1_symbol="USDT",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=None,
            tick_spacing=None,
            pool_tick=200000,
            current_tick=200000,
            current_price_token1_per_token0=Decimal("2000"),
            onchain_liquidity=Decimal("1"),
        )
        use_case = GetLiquidityDistributionDefaultRangeUseCase(
            distribution_port=FakeDistributionPort(pool)
        )

        with self.assertRaises(LiquidityDistributionInputError):
            use_case.execute(
                GetLiquidityDistributionDefaultRangeInput(
                    pool_id=1,
                    chain_id=None,
                    dex_id=None,
                    snapshot_date=date(2026, 2, 16),
                    preset="wide",
                    initial_price=None,
                    center_tick=None,
                    swapped_pair=False,
                )
            )

    def test_swapped_pair_inverts_ticks_and_prices_for_ui_reference(self):
        pool = LiquidityDistributionPool(
            id=1,
            token0_symbol="WETH",
            token1_symbol="USDT",
            token0_decimals=0,
            token1_decimals=0,
            fee_tier=3000,
            tick_spacing=60,
            pool_tick=12000,
            current_tick=12000,
            current_price_token1_per_token0=Decimal("3"),
            onchain_liquidity=Decimal("1"),
        )
        use_case = GetLiquidityDistributionDefaultRangeUseCase(
            distribution_port=FakeDistributionPort(pool)
        )

        canonical = use_case.execute(
            GetLiquidityDistributionDefaultRangeInput(
                pool_id=1,
                chain_id=None,
                dex_id=None,
                snapshot_date=date(2026, 2, 16),
                preset="wide",
                initial_price=Decimal("3"),
                center_tick=-12000,
                swapped_pair=False,
            )
        )
        swapped = use_case.execute(
            GetLiquidityDistributionDefaultRangeInput(
                pool_id=1,
                chain_id=None,
                dex_id=None,
                snapshot_date=date(2026, 2, 16),
                preset="wide",
                initial_price=Decimal("0.3333333333333333"),
                center_tick=12000,
                swapped_pair=True,
            )
        )

        self.assertEqual(swapped.min_tick, -canonical.max_tick)
        self.assertEqual(swapped.max_tick, -canonical.min_tick)
        self.assertAlmostEqual(swapped.min_price, 1 / canonical.max_price, places=12)
        self.assertAlmostEqual(swapped.max_price, 1 / canonical.min_price, places=12)


if __name__ == "__main__":
    unittest.main()
