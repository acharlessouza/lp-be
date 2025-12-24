from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import httpx


class SubgraphError(RuntimeError):
    pass


@dataclass(frozen=True)
class UniswapV3SubgraphClient:
    graph_api_key: str
    graph_gateway_base: str
    subgraph_ids: dict
    timeout_seconds: float

    def get_current_tick(self, *, network: str, pool_address: str) -> int:
        endpoint = self._get_endpoint(network)
        query = {
            "query": f'{{ pool(id: "{pool_address.lower()}") {{ tick }} }}',
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(endpoint, json=query)
            response.raise_for_status()
            payload = response.json()
        if "errors" in payload:
            raise SubgraphError("Subgraph error while fetching current tick.")
        pool = payload.get("data", {}).get("pool")
        if not pool or pool.get("tick") is None:
            raise SubgraphError("Pool not found in subgraph.")
        return int(pool["tick"])

    def get_current_price(self, *, network: str, pool_address: str) -> Decimal:
        endpoint = self._get_endpoint(network)
        query = {
            "query": f'{{ pool(id: "{pool_address.lower()}") {{ token1Price }} }}',
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(endpoint, json=query)
            response.raise_for_status()
            payload = response.json()
        if "errors" in payload:
            raise SubgraphError("Subgraph error while fetching current price.")
        pool = payload.get("data", {}).get("pool")
        price_value = pool.get("token1Price") if pool else None
        if price_value is None:
            raise SubgraphError("Pool price not found in subgraph.")
        return Decimal(str(price_value))

    def _get_endpoint(self, network: str) -> str:
        if not self.graph_api_key:
            raise SubgraphError("GRAPH_API_KEY is required for subgraph access.")
        key = network.strip().lower()
        subgraph_id = self.subgraph_ids.get(key)
        if not subgraph_id:
            raise SubgraphError(f"Subgraph ID not configured for network: {network}")
        return f"{self.graph_gateway_base}/{self.graph_api_key}/subgraphs/id/{subgraph_id}"
