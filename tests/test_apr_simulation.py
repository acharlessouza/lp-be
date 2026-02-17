from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from app.domain.entities.simulate_apr import SimulateAprHourly, SimulateAprInitializedTick
from app.domain.services.apr_simulation import simulate_fee_apr
from app.domain.services.liquidity import build_liquidity_curve


class AprSimulationDomainTests(unittest.TestCase):
    def test_in_range_generates_fees_and_annualization(self):
        base = datetime(2026, 1, 1, 0, 0, 0)
        hourly_fees = [
            SimulateAprHourly(hour_ts=base + timedelta(hours=i), fees_usd=Decimal("10"), volume_usd=None)
            for i in range(3)
        ]
        curve = build_liquidity_curve(
            [
                SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("100")),
            ]
        )
        result = simulate_fee_apr(
            hourly_fees=hourly_fees,
            hourly_ticks={},
            hourly_liquidity={},
            liquidity_curve=curve,
            l_user=Decimal("100"),
            tick_lower=0,
            tick_upper=10,
            full_range=False,
            mode="A",
            fallback_tick=5,
            latest_pool_liquidity=None,
            horizon_hours=24,
            annualization_days=1,
            deposit_usd=Decimal("1000"),
        )

        self.assertEqual(result.diagnostics.hours_total, 3)
        self.assertEqual(result.diagnostics.hours_in_range, 3)
        self.assertEqual(result.estimated_fees_24h_usd, Decimal("120"))
        self.assertEqual(result.monthly_usd, Decimal("3600"))
        self.assertEqual(result.yearly_usd, Decimal("43800"))
        self.assertEqual(result.fee_apr, Decimal("43.8"))

    def test_out_of_range_produces_zero_fees(self):
        base = datetime(2026, 1, 1, 0, 0, 0)
        hourly_fees = [
            SimulateAprHourly(hour_ts=base + timedelta(hours=i), fees_usd=Decimal("10"), volume_usd=None)
            for i in range(5)
        ]
        curve = build_liquidity_curve(
            [
                SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("100")),
            ]
        )
        result = simulate_fee_apr(
            hourly_fees=hourly_fees,
            hourly_ticks={},
            hourly_liquidity={},
            liquidity_curve=curve,
            l_user=Decimal("100"),
            tick_lower=0,
            tick_upper=10,
            full_range=False,
            mode="A",
            fallback_tick=100,
            latest_pool_liquidity=None,
            horizon_hours=24,
            annualization_days=1,
            deposit_usd=Decimal("1000"),
        )

        self.assertEqual(result.diagnostics.hours_in_range, 0)
        self.assertEqual(result.estimated_fees_24h_usd, Decimal("0"))
        self.assertEqual(result.monthly_usd, Decimal("0"))
        self.assertEqual(result.yearly_usd, Decimal("0"))
        self.assertEqual(result.fee_apr, Decimal("0"))

    def test_full_range_is_always_in_range_and_uses_snapshot_liquidity(self):
        base = datetime(2026, 1, 1, 0, 0, 0)
        hourly_fees = [
            SimulateAprHourly(hour_ts=base + timedelta(hours=i), fees_usd=Decimal("10"), volume_usd=None)
            for i in range(3)
        ]
        result = simulate_fee_apr(
            hourly_fees=hourly_fees,
            hourly_ticks={},
            hourly_liquidity={
                base: Decimal("100"),
                base + timedelta(hours=2): Decimal("300"),
            },
            liquidity_curve=build_liquidity_curve([]),
            l_user=Decimal("100"),
            tick_lower=0,
            tick_upper=10,
            full_range=True,
            mode="A",
            fallback_tick=100,
            latest_pool_liquidity=Decimal("200"),
            horizon_hours=24,
            annualization_days=1,
            deposit_usd=Decimal("1000"),
        )

        self.assertEqual(result.diagnostics.hours_total, 3)
        self.assertEqual(result.diagnostics.hours_in_range, 3)
        self.assertEqual(result.diagnostics.percent_time_in_range, Decimal("100"))
        self.assertGreater(result.estimated_fees_24h_usd, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
