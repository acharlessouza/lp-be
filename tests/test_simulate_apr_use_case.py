from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from app.application.dto.simulate_apr import SimulateAprInput
from app.application.use_cases.simulate_apr import SimulateAprUseCase
from app.domain.entities.simulate_apr import (
    SimulateAprHourly,
    SimulateAprInitializedTick,
    SimulateAprPool,
    SimulateAprPoolState,
    SimulateAprSnapshotHourly,
)


class FakeSimulateAprPort:
    def get_pool(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPool | None:
        _ = (pool_address, chain_id, dex_id)
        return SimulateAprPool(
            dex_id=2,
            chain_id=1,
            pool_address="0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=60,
        )

    def get_latest_pool_state(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPoolState | None:
        _ = (pool_address, chain_id, dex_id)
        return SimulateAprPoolState(
            tick=-200000,
            sqrt_price_x96=None,
            price_token0_per_token1=Decimal("2000"),
            liquidity=Decimal("1000000"),
        )

    def get_pool_hourly(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        hours: int,
    ) -> list[SimulateAprHourly]:
        _ = (pool_address, chain_id, dex_id)
        base = datetime(2026, 1, 1, 0, 0, 0)
        return [
            SimulateAprHourly(
                hour_ts=base + timedelta(hours=i),
                fees_usd=Decimal("12"),
                volume_usd=Decimal("100"),
            )
            for i in range(min(hours, 48))
        ]

    def get_pool_state_snapshots_hourly(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        hours: int,
    ) -> list[SimulateAprSnapshotHourly]:
        _ = (pool_address, chain_id, dex_id, hours)
        return []

    def get_initialized_ticks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        min_tick: int,
        max_tick: int,
    ) -> list[SimulateAprInitializedTick]:
        _ = (pool_address, chain_id, dex_id, min_tick, max_tick)
        return [
            SimulateAprInitializedTick(tick_idx=-300000, liquidity_net=Decimal("1000000")),
            SimulateAprInitializedTick(tick_idx=-150000, liquidity_net=Decimal("-1000")),
        ]


class SimulateAprUseCaseTests(unittest.TestCase):
    def test_use_case_mode_b_with_missing_snapshots_adds_warning(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        result = use_case.execute(
            SimulateAprInput(
                pool_address="0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
                chain_id=1,
                dex_id=2,
                deposit_usd=None,
                amount_token0=Decimal("1"),
                amount_token1=Decimal("500"),
                tick_lower=-210000,
                tick_upper=-190000,
                min_price=None,
                max_price=None,
                horizon="7d",
                mode="B",
                lookback_days=2,
            )
        )

        self.assertGreater(result.estimated_fees_24h_usd, Decimal("0"))
        self.assertGreater(result.monthly_usd, Decimal("0"))
        self.assertGreater(result.yearly_usd, Decimal("0"))
        self.assertGreaterEqual(result.fee_apr, Decimal("0"))
        self.assertIn("mode", result.diagnostics.assumptions)
        self.assertTrue(any("mode B" in warning for warning in result.diagnostics.warnings))
        self.assertTrue(
            any("Insufficient hourly data" in warning for warning in result.diagnostics.warnings)
        )

    def test_use_case_derives_amounts_from_deposit_when_amounts_are_missing(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        result = use_case.execute(
            SimulateAprInput(
                pool_address="0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
                chain_id=1,
                dex_id=2,
                deposit_usd=Decimal("1000"),
                amount_token0=None,
                amount_token1=None,
                tick_lower=-210000,
                tick_upper=-190000,
                min_price=None,
                max_price=None,
                horizon="24h",
                mode="A",
                lookback_days=2,
            )
        )

        self.assertGreater(result.estimated_fees_24h_usd, Decimal("0"))
        self.assertTrue(
            any("Derived token amounts" in warning for warning in result.diagnostics.warnings)
        )

    def test_use_case_accepts_dynamic_horizon(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        result = use_case.execute(
            SimulateAprInput(
                pool_address="0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
                chain_id=1,
                dex_id=2,
                deposit_usd=Decimal("1000"),
                amount_token0=Decimal("1"),
                amount_token1=Decimal("0"),
                tick_lower=-210000,
                tick_upper=-190000,
                min_price=None,
                max_price=None,
                horizon="14d",
                mode="A",
                lookback_days=14,
            )
        )

        self.assertEqual(result.diagnostics.assumptions["annualization"], "14d")


if __name__ == "__main__":
    unittest.main()
