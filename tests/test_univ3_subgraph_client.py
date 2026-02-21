from __future__ import annotations

from app.infrastructure.clients.univ3_subgraph_client import (
    Univ3SubgraphClient,
    Univ3SubgraphClientSettings,
)


def _make_client() -> Univ3SubgraphClient:
    return Univ3SubgraphClient(
        Univ3SubgraphClientSettings(
            graph_gateway_base="https://gateway.thegraph.com/api",
            graph_api_key="api-key",
            graph_subgraph_ids={"ethereum": "subgraph-id"},
            graph_blocks_subgraph_ids={"ethereum": "blocks-id"},
            timeout_seconds=10,
            max_retries=1,
            min_interval_ms=0,
        )
    )


def test_build_gateway_url_uses_id_when_value_is_not_url():
    client = _make_client()
    url = client._build_gateway_url("9A6bkprqEG2XsZUYJ5B2XXp6ymz9fNcn4tVPxMWDztYC")
    assert url == (
        "https://gateway.thegraph.com/api/api-key/subgraphs/id/"
        "9A6bkprqEG2XsZUYJ5B2XXp6ymz9fNcn4tVPxMWDztYC"
    )


def test_build_gateway_url_keeps_full_url_unchanged():
    client = _make_client()
    full_url = (
        "https://gateway.thegraph.com/api/api-key/subgraphs/id/"
        "9A6bkprqEG2XsZUYJ5B2XXp6ymz9fNcn4tVPxMWDztYC"
    )
    assert client._build_gateway_url(full_url) == full_url
