from __future__ import annotations

import ast
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
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
from app.domain.exceptions import InvalidSimulationInputError
from app.domain.services.liquidity import build_liquidity_curve
from app.domain.services.univ3_math import (
    sqrt_price_x96_to_price,
    tick_to_price,
    tick_to_sqrt_price_x96,
)


class FakeSimulateAprPort:
    def __init__(self):
        self._pool = SimulateAprPool(
            dex_id=2,
            chain_id=1,
            pool_address="0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=60,
        )
        self._latest_state = SimulateAprPoolState(
            tick=-200000,
            sqrt_price_x96=None,
            liquidity=Decimal("1000000"),
        )

    def get_pool(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPool | None:
        _ = (pool_address, chain_id, dex_id)
        return self._pool

    def get_latest_pool_state(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprPoolState | None:
        _ = (pool_address, chain_id, dex_id)
        return self._latest_state

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
    def _base_input(self, **overrides) -> SimulateAprInput:
        payload = {
            "pool_address": "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36",
            "chain_id": 1,
            "dex_id": 2,
            "deposit_usd": Decimal("1000"),
            "amount_token0": Decimal("1"),
            "amount_token1": Decimal("0"),
            "tick_lower": -210000,
            "tick_upper": -190000,
            "min_price": None,
            "max_price": None,
            "horizon": "14d",
            "mode": "A",
            "calculation_method": "current",
            "custom_calculation_price": None,
            "lookback_days": 14,
        }
        payload.update(overrides)
        return SimulateAprInput(**payload)

    def test_custom_method_requires_positive_custom_price(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        with self.assertRaises(InvalidSimulationInputError):
            use_case.execute(
                self._base_input(
                    calculation_method="custom",
                    custom_calculation_price=None,
                )
            )
        with self.assertRaises(InvalidSimulationInputError):
            use_case.execute(
                self._base_input(
                    calculation_method="custom",
                    custom_calculation_price=Decimal("0"),
                )
            )

    def test_current_method_uses_sqrt_price_when_available(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        pool = SimulateAprPool(
            dex_id=2,
            chain_id=1,
            pool_address="0xpool",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=60,
        )
        sqrt_tick = -201000
        sqrt_x96 = tick_to_sqrt_price_x96(sqrt_tick)
        latest_state = SimulateAprPoolState(
            tick=-150000,
            sqrt_price_x96=sqrt_x96,
            liquidity=Decimal("1"),
        )
        curve = build_liquidity_curve([SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("1"))])
        price = use_case._resolve_calculation_price(
            method="current",
            custom_price=None,
            current_tick=-150000,
            latest_state=latest_state,
            pool=pool,
            liquidity_curve=curve,
            tick_lower=-10,
            tick_upper=10,
            initialized_ticks=[SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("1"))],
            warnings=[],
        )

        expected = sqrt_price_x96_to_price(sqrt_x96, pool.token0_decimals, pool.token1_decimals)
        self.assertEqual(price, expected)

    def test_current_method_falls_back_to_tick_when_no_sqrt(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        pool = SimulateAprPool(
            dex_id=2,
            chain_id=1,
            pool_address="0xpool",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=60,
        )
        current_tick = -199500
        latest_state = SimulateAprPoolState(
            tick=current_tick,
            sqrt_price_x96=None,
            liquidity=Decimal("1"),
        )
        curve = build_liquidity_curve([SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("1"))])
        price = use_case._resolve_calculation_price(
            method="current",
            custom_price=None,
            current_tick=current_tick,
            latest_state=latest_state,
            pool=pool,
            liquidity_curve=curve,
            tick_lower=-10,
            tick_upper=10,
            initialized_ticks=[SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("1"))],
            warnings=[],
        )

        self.assertEqual(price, tick_to_price(current_tick, pool.token0_decimals, pool.token1_decimals))

    def test_peak_liquidity_in_range_uses_peak_tick_price(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        pool = SimulateAprPool(
            dex_id=2,
            chain_id=1,
            pool_address="0xpool",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=60,
        )
        latest_state = SimulateAprPoolState(
            tick=20,
            sqrt_price_x96=None,
            liquidity=Decimal("1"),
        )
        initialized_ticks = [
            SimulateAprInitializedTick(tick_idx=-100, liquidity_net=Decimal("100")),
            SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("50")),
            SimulateAprInitializedTick(tick_idx=100, liquidity_net=Decimal("-120")),
            SimulateAprInitializedTick(tick_idx=200, liquidity_net=Decimal("-30")),
        ]
        curve = build_liquidity_curve(initialized_ticks)

        price = use_case._resolve_calculation_price(
            method="peak_liquidity_in_range",
            custom_price=None,
            current_tick=20,
            latest_state=latest_state,
            pool=pool,
            liquidity_curve=curve,
            tick_lower=-100,
            tick_upper=100,
            initialized_ticks=initialized_ticks,
            warnings=[],
        )

        self.assertEqual(price, tick_to_price(0, pool.token0_decimals, pool.token1_decimals))

    def test_avg_liquidity_in_range_uses_weighted_avg_tick_price(self):
        use_case = SimulateAprUseCase(simulate_apr_port=FakeSimulateAprPort())
        pool = SimulateAprPool(
            dex_id=2,
            chain_id=1,
            pool_address="0xpool",
            token0_decimals=18,
            token1_decimals=6,
            fee_tier=3000,
            tick_spacing=60,
        )
        latest_state = SimulateAprPoolState(
            tick=20,
            sqrt_price_x96=None,
            liquidity=Decimal("1"),
        )
        initialized_ticks = [
            SimulateAprInitializedTick(tick_idx=-100, liquidity_net=Decimal("100")),
            SimulateAprInitializedTick(tick_idx=0, liquidity_net=Decimal("50")),
            SimulateAprInitializedTick(tick_idx=100, liquidity_net=Decimal("-120")),
            SimulateAprInitializedTick(tick_idx=200, liquidity_net=Decimal("-30")),
        ]
        curve = build_liquidity_curve(initialized_ticks)

        price = use_case._resolve_calculation_price(
            method="avg_liquidity_in_range",
            custom_price=None,
            current_tick=20,
            latest_state=latest_state,
            pool=pool,
            liquidity_curve=curve,
            tick_lower=-100,
            tick_upper=100,
            initialized_ticks=initialized_ticks,
            warnings=[],
        )

        self.assertEqual(price, tick_to_price(-25, pool.token0_decimals, pool.token1_decimals))

    def test_response_schema_has_no_diagnostics_field(self):
        source = Path("app/api/schemas/simulate_apr.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        response_fields: set[str] = set()
        for node in module.body:
            if isinstance(node, ast.ClassDef) and node.name == "SimulateAprResponse":
                for class_node in node.body:
                    if isinstance(class_node, ast.AnnAssign) and isinstance(class_node.target, ast.Name):
                        response_fields.add(class_node.target.id)
        self.assertNotIn("diagnostics", response_fields)


if __name__ == "__main__":
    unittest.main()
