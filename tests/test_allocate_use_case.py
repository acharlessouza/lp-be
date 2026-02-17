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


if __name__ == "__main__":
    unittest.main()
