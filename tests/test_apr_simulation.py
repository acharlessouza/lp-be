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
            liquidity_curve=curve,
            l_user=Decimal("100"),
            tick_lower=0,
            tick_upper=10,
            mode="A",
            fallback_tick=5,
            horizon_hours=24,
            annualization_days=1,
            deposit_usd=Decimal("1000"),
        )

        self.assertEqual(result.diagnostics.hours_total, 3)
        self.assertEqual(result.diagnostics.hours_in_range, 3)
        self.assertEqual(result.estimated_fees_24h_usd, Decimal("15"))
        self.assertEqual(result.monthly_usd, Decimal("450"))
        self.assertEqual(result.yearly_usd, Decimal("5475"))
        self.assertEqual(result.fee_apr, Decimal("5.475"))

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
            liquidity_curve=curve,
            l_user=Decimal("100"),
            tick_lower=0,
            tick_upper=10,
            mode="A",
            fallback_tick=100,
            horizon_hours=24,
            annualization_days=1,
            deposit_usd=Decimal("1000"),
        )

        self.assertEqual(result.diagnostics.hours_in_range, 0)
        self.assertEqual(result.estimated_fees_24h_usd, Decimal("0"))
        self.assertEqual(result.monthly_usd, Decimal("0"))
        self.assertEqual(result.yearly_usd, Decimal("0"))
        self.assertEqual(result.fee_apr, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
