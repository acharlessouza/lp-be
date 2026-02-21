from __future__ import annotations

from decimal import Decimal
import unittest

from app.application.dto.allocate import AllocateInput
from app.application.use_cases.allocate import AllocateUseCase
from app.domain.entities.pool import Pool
from app.domain.exceptions import AllocationInputError


class FakePoolPort:
    def get_by_address(self, *, pool_address: str, chain_id: int, dex_id: int) -> Pool | None:
        _ = (pool_address, chain_id, dex_id)
        return Pool(
            network="arbitrum",
            pool_address="0xpool",
            fee_tier=500,
            token0_address="0xt0",
            token0_symbol="WETH",
            token1_address="0xt1",
            token1_symbol="USDC",
        )


class FakePricePort:
    def get_pair_prices(
        self,
        *,
        token0_address: str,
        token1_address: str,
        network: str,
    ) -> tuple[Decimal, Decimal]:
        _ = (token0_address, token1_address, network)
        return Decimal("2000"), Decimal("1")


class AllocateUseCaseTests(unittest.TestCase):
    def _base_input(self, **overrides) -> AllocateInput:
        payload = {
            "pool_address": "0xpool",
            "chain_id": 42161,
            "dex_id": 1,
            "deposit_usd": Decimal("1000"),
            "full_range": False,
            "range_min": Decimal("1500"),
            "range_max": Decimal("2500"),
        }
        payload.update(overrides)
        return AllocateInput(**payload)

    def test_full_range_splits_approximately_50_50_in_usd_value(self):
        use_case = AllocateUseCase(pool_port=FakePoolPort(), price_port=FakePricePort())
        result = use_case.execute(
            self._base_input(
                full_range=True,
                range_min=None,
                range_max=None,
            )
        )

        value0 = result.amount_token0 * result.price_token0_usd
        value1 = result.amount_token1 * result.price_token1_usd
        self.assertEqual(value0, Decimal("500"))
        self.assertEqual(value1, Decimal("500"))

    def test_full_range_does_not_require_ranges(self):
        use_case = AllocateUseCase(pool_port=FakePoolPort(), price_port=FakePricePort())
        result = use_case.execute(
            self._base_input(
                full_range=True,
                range_min=None,
                range_max=None,
            )
        )
        self.assertGreater(result.amount_token0, Decimal("0"))
        self.assertGreater(result.amount_token1, Decimal("0"))

    def test_custom_range_requires_range_values(self):
        use_case = AllocateUseCase(pool_port=FakePoolPort(), price_port=FakePricePort())
        with self.assertRaises(AllocationInputError):
            use_case.execute(
                self._base_input(
                    full_range=False,
                    range_min=None,
                    range_max=None,
                )
            )

    def test_swapped_pair_converts_range_and_returns_amounts_in_ui_orientation(self):
        use_case = AllocateUseCase(pool_port=FakePoolPort(), price_port=FakePricePort())

        min_ui = Decimal("0.0004")
        max_ui = Decimal("0.0006")
        min_canonical = Decimal("1") / max_ui
        max_canonical = Decimal("1") / min_ui

        canonical = use_case.execute(
            self._base_input(
                full_range=False,
                range_min=min_canonical,
                range_max=max_canonical,
                swapped_pair=False,
            )
        )
        swapped = use_case.execute(
            self._base_input(
                full_range=False,
                range_min=min_ui,
                range_max=max_ui,
                swapped_pair=True,
            )
        )

        self.assertEqual(swapped.token0_symbol, canonical.token1_symbol)
        self.assertEqual(swapped.token1_symbol, canonical.token0_symbol)
        self.assertEqual(swapped.amount_token0, canonical.amount_token1)
        self.assertEqual(swapped.amount_token1, canonical.amount_token0)
        self.assertEqual(swapped.price_token0_usd, canonical.price_token1_usd)
        self.assertEqual(swapped.price_token1_usd, canonical.price_token0_usd)

    def test_swapped_pair_swaps_full_range_output(self):
        use_case = AllocateUseCase(pool_port=FakePoolPort(), price_port=FakePricePort())

        canonical = use_case.execute(
            self._base_input(
                full_range=True,
                range_min=None,
                range_max=None,
                swapped_pair=False,
            )
        )
        swapped = use_case.execute(
            self._base_input(
                full_range=True,
                range_min=None,
                range_max=None,
                swapped_pair=True,
            )
        )

        self.assertEqual(swapped.token0_symbol, canonical.token1_symbol)
        self.assertEqual(swapped.token1_symbol, canonical.token0_symbol)
        self.assertEqual(swapped.amount_token0, canonical.amount_token1)
        self.assertEqual(swapped.amount_token1, canonical.amount_token0)


if __name__ == "__main__":
    unittest.main()
