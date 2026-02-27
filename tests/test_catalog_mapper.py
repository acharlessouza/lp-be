from __future__ import annotations

import unittest

from app.infrastructure.db.mappers.catalog_mapper import (
    map_row_to_exchange,
    map_row_to_network,
    map_row_to_pool_detail,
    map_row_to_token,
)


class CatalogMapperTests(unittest.TestCase):
    def test_map_row_to_exchange_includes_icon_url(self):
        row = {
            "id": 1,
            "name": "uniswap",
            "icon_url": "https://cdn.example.com/uniswap.png",
        }

        exchange = map_row_to_exchange(row)

        self.assertEqual(exchange.id, 1)
        self.assertEqual(exchange.name, "uniswap")
        self.assertEqual(exchange.icon_url, "https://cdn.example.com/uniswap.png")

    def test_map_row_to_network_includes_icon_url(self):
        row = {
            "id": 42161,
            "name": "arbitrum",
            "icon_url": "https://cdn.example.com/arbitrum.png",
        }

        network = map_row_to_network(row)

        self.assertEqual(network.id, 42161)
        self.assertEqual(network.name, "arbitrum")
        self.assertEqual(network.icon_url, "https://cdn.example.com/arbitrum.png")

    def test_map_row_to_token_includes_icon_url(self):
        row = {
            "address": "0xt0",
            "symbol": "WETH",
            "decimals": 18,
            "icon_url": "https://cdn.example.com/weth.png",
        }

        token = map_row_to_token(row)

        self.assertEqual(token.address, "0xt0")
        self.assertEqual(token.symbol, "WETH")
        self.assertEqual(token.decimals, 18)
        self.assertEqual(token.icon_url, "https://cdn.example.com/weth.png")

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
