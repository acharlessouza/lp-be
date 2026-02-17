from __future__ import annotations

from decimal import Decimal
import unittest

from app.application.dto.pool_volume_history import GetPoolVolumeHistoryInput
from app.application.use_cases.get_pool_volume_history import GetPoolVolumeHistoryUseCase
from app.domain.entities.pool_volume_history import (
    PoolVolumeHistoryPoint,
    PoolVolumeHistorySummaryBase,
    PoolVolumeHistorySummaryPremium,
)
from app.domain.exceptions import PoolVolumeHistoryInputError


class FakePoolVolumeHistoryPort:
    def __init__(self):
        self.called_base = False
        self.called_premium = False
        self.last_premium_call: dict[str, str | int | None] | None = None

    def list_daily_volume_history(
        self,
        *,
        pool_address: str,
        days: int,
        chain_id: int | None,
        dex_id: int | None,
    ):
        _ = (pool_address, days, chain_id, dex_id)
        return [
            PoolVolumeHistoryPoint(
                time="2026-02-10",
                value=Decimal("100.50"),
                fees_usd=Decimal("1.25"),
            ),
            PoolVolumeHistoryPoint(
                time="2026-02-09",
                value=Decimal("90.00"),
                fees_usd=Decimal("1.10"),
            ),
        ]

    def get_summary_base(
        self,
        *,
        pool_address: str,
        days: int,
        chain_id: int | None,
        dex_id: int | None,
    ) -> PoolVolumeHistorySummaryBase:
        _ = (pool_address, days, chain_id, dex_id)
        self.called_base = True
        return PoolVolumeHistorySummaryBase(
            tvl_usd=Decimal("1000"),
            avg_daily_fees_usd=Decimal("10"),
            avg_daily_volume_usd=Decimal("100"),
            token0_symbol="WETH",
            token1_symbol="USDC",
        )

    def get_summary_premium(
        self,
        *,
        exchange: str,
        symbol0: str,
        symbol1: str | None,
        days: int,
    ) -> PoolVolumeHistorySummaryPremium:
        self.last_premium_call = {
            "exchange": exchange,
            "symbol0": symbol0,
            "symbol1": symbol1,
            "days": days,
        }
        self.called_premium = True
        return PoolVolumeHistorySummaryPremium(
            price_volatility_pct=Decimal("1.23"),
            correlation=Decimal("0.55"),
            geometric_mean_price=Decimal("2222.22"),
        )


class PoolVolumeHistoryUseCaseTests(unittest.TestCase):
    def _base_input(self, **overrides) -> GetPoolVolumeHistoryInput:
        payload = {
            "pool_address": "0xabc",
            "days": 7,
            "chain_id": 42161,
            "dex_id": 1,
            "include_premium": False,
            "exchange": "binance",
            "symbol0": None,
            "symbol1": None,
        }
        payload.update(overrides)
        return GetPoolVolumeHistoryInput(**payload)

    def test_invalid_days_raises(self):
        use_case = GetPoolVolumeHistoryUseCase(pool_volume_history_port=FakePoolVolumeHistoryPort())
        with self.assertRaises(PoolVolumeHistoryInputError):
            use_case.execute(self._base_input(days=0))

    def test_missing_symbols_keeps_premium_fields_as_null(self):
        use_case = GetPoolVolumeHistoryUseCase(pool_volume_history_port=FakePoolVolumeHistoryPort())
        result = use_case.execute(self._base_input(include_premium=True))
        self.assertIsNotNone(result.summary)
        assert result.summary is not None
        self.assertIsNone(result.summary.price_volatility_pct)
        self.assertIsNone(result.summary.correlation)
        self.assertIsNone(result.summary.geometric_mean_price)

    def test_graph_payload_kept_and_sorted_with_summary(self):
        port = FakePoolVolumeHistoryPort()
        use_case = GetPoolVolumeHistoryUseCase(pool_volume_history_port=port)
        result = use_case.execute(self._base_input())

        self.assertIsNotNone(result.summary)
        self.assertEqual(len(result.volume_history), 2)
        self.assertEqual(result.volume_history[0].time, "2026-02-09")
        self.assertEqual(result.volume_history[0].value, Decimal("90.00"))
        self.assertEqual(result.volume_history[0].fees_usd, Decimal("1.10"))
        self.assertEqual(result.volume_history[1].time, "2026-02-10")
        self.assertTrue(port.called_base)
        self.assertFalse(port.called_premium)

    def test_summary_without_premium_flag_still_populates_base_metrics(self):
        port = FakePoolVolumeHistoryPort()
        use_case = GetPoolVolumeHistoryUseCase(pool_volume_history_port=port)
        result = use_case.execute(self._base_input(include_premium=False))

        self.assertIsNotNone(result.summary)
        assert result.summary is not None
        self.assertEqual(result.summary.tvl_usd, Decimal("1000"))
        self.assertEqual(result.summary.avg_daily_fees_usd, Decimal("1.175"))
        self.assertEqual(result.summary.avg_daily_volume_usd, Decimal("95.25"))
        self.assertEqual(result.summary.daily_fees_tvl_pct, Decimal("0.117500"))
        self.assertEqual(result.summary.daily_volume_tvl_pct, Decimal("9.52500"))
        self.assertIsNone(result.summary.price_volatility_pct)
        self.assertIsNone(result.summary.correlation)
        self.assertIsNone(result.summary.geometric_mean_price)
        self.assertTrue(port.called_base)
        self.assertFalse(port.called_premium)

    def test_summary_with_premium_flag_keeps_fields_as_null(self):
        port = FakePoolVolumeHistoryPort()
        use_case = GetPoolVolumeHistoryUseCase(pool_volume_history_port=port)
        result = use_case.execute(
            self._base_input(
                include_premium=True,
                symbol0="WETH",
                symbol1="USDT",
            )
        )

        self.assertIsNotNone(result.summary)
        assert result.summary is not None
        self.assertIsNone(result.summary.price_volatility_pct)
        self.assertIsNone(result.summary.correlation)
        self.assertIsNone(result.summary.geometric_mean_price)
        self.assertTrue(port.called_base)
        self.assertFalse(port.called_premium)

    def test_even_with_symbols_premium_fields_stay_null(self):
        port = FakePoolVolumeHistoryPort()
        use_case = GetPoolVolumeHistoryUseCase(pool_volume_history_port=port)
        result = use_case.execute(
            self._base_input(
                include_premium=False,
                symbol0="WETH/USDT",
            )
        )

        self.assertIsNotNone(result.summary)
        assert result.summary is not None
        self.assertIsNone(result.summary.price_volatility_pct)
        self.assertIsNone(result.summary.correlation)
        self.assertIsNone(result.summary.geometric_mean_price)
        self.assertFalse(port.called_premium)


if __name__ == "__main__":
    unittest.main()
