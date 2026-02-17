from __future__ import annotations

import unittest

from app.infrastructure.db.mappers.catalog_mapper import map_row_to_pool_detail


class CatalogMapperTests(unittest.TestCase):
    def test_map_row_to_pool_detail_includes_dex_and_chain(self):
        row = {
            "id": "0xpool",
            "dex_key": "uniswap-v3",
            "dex_name": "Uniswap",
            "dex_version": "v3",
            "chain_key": "arbitrum",
            "chain_name": "Arbitrum",
            "fee_tier": 500,
            "token0_address": "0xt0",
            "token0_symbol": "WETH",
            "token0_decimals": 18,
            "token1_address": "0xt1",
            "token1_symbol": "USDT",
            "token1_decimals": 6,
        }

        detail = map_row_to_pool_detail(row)

        self.assertEqual(detail.id, "0xpool")
        self.assertEqual(detail.dex_key, "uniswap-v3")
        self.assertEqual(detail.dex_name, "Uniswap")
        self.assertEqual(detail.dex_version, "v3")
        self.assertEqual(detail.chain_key, "arbitrum")
        self.assertEqual(detail.chain_name, "Arbitrum")
        self.assertEqual(detail.fee_tier, 500)
        self.assertEqual(detail.token0_symbol, "WETH")
        self.assertEqual(detail.token1_symbol, "USDT")


if __name__ == "__main__":
    unittest.main()
