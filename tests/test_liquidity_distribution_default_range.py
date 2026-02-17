from __future__ import annotations

import unittest

from app.domain.services.liquidity_distribution_default_range import (
    align_tick_ceil,
    align_tick_floor,
    calculate_preset_range,
    price_to_tick_ceil,
    price_to_tick_floor,
    tick_to_price,
)


class LiquidityDistributionDefaultRangeDomainTests(unittest.TestCase):
    def test_stable_uses_plus_minus_3_usable_ticks(self):
        min_price, max_price, min_tick, max_tick = calculate_preset_range(
            preset="stable",
            current_tick=12345,
            current_price=2000,
            tick_spacing=60,
            swapped_pair=False,
            token0_decimals=0,
            token1_decimals=0,
        )

        self.assertEqual(min_tick, 12120)
        self.assertEqual(max_tick, 12480)
        self.assertAlmostEqual(min_price, tick_to_price(12120, 0, 0), places=12)
        self.assertAlmostEqual(max_price, tick_to_price(12480, 0, 0), places=12)

    def test_wide_aligns_ticks_outward_with_tick_spacing(self):
        min_price, max_price, min_tick, max_tick = calculate_preset_range(
            preset="wide",
            current_tick=10000,
            current_price=2000,
            tick_spacing=60,
            swapped_pair=False,
            token0_decimals=0,
            token1_decimals=0,
        )

        min_tick_raw = price_to_tick_floor(1000, 0, 0)
        max_tick_raw = price_to_tick_ceil(4000, 0, 0)
        self.assertEqual(min_tick, align_tick_floor(min_tick_raw, 60))
        self.assertEqual(max_tick, align_tick_ceil(max_tick_raw, 60))
        self.assertLess(min_price, max_price)
        self.assertEqual(min_tick % 60, 0)
        self.assertEqual(max_tick % 60, 0)

    def test_swapped_pair_inverts_price_and_keeps_ordering(self):
        min_price, max_price, min_tick, max_tick = calculate_preset_range(
            preset="wide",
            current_tick=10000,
            current_price=2000,
            tick_spacing=60,
            swapped_pair=True,
            token0_decimals=0,
            token1_decimals=0,
        )

        base_price_min_tick = tick_to_price(min_tick, 0, 0)
        base_price_max_tick = tick_to_price(max_tick, 0, 0)
        expected_min = min(1 / base_price_min_tick, 1 / base_price_max_tick)
        expected_max = max(1 / base_price_min_tick, 1 / base_price_max_tick)
        self.assertAlmostEqual(min_price, expected_min, places=12)
        self.assertAlmostEqual(max_price, expected_max, places=12)
        self.assertLess(min_price, max_price)

    def test_price_to_tick_uses_floor_and_ceil_without_round(self):
        price_100_6 = tick_to_price(100.6, 0, 0)
        price_100_4 = tick_to_price(100.4, 0, 0)

        self.assertEqual(price_to_tick_floor(price_100_6, 0, 0), 100)
        self.assertEqual(price_to_tick_ceil(price_100_6, 0, 0), 101)
        self.assertEqual(price_to_tick_floor(price_100_4, 0, 0), 100)
        self.assertEqual(price_to_tick_ceil(price_100_4, 0, 0), 101)


if __name__ == "__main__":
    unittest.main()
