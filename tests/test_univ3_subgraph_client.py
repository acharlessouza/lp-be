from __future__ import annotations

import pytest

from app.application.dto.tick_snapshot_on_demand import InitializedTickSourceRow
from app.infrastructure.clients.univ3_subgraph_client import (
    Univ3SubgraphClient,
    Univ3SubgraphClientSettings,
)
from app.infrastructure.db.repositories.tick_snapshot_on_demand_repository import (
    SqlTickSnapshotOnDemandRepository,
)


def _make_client(*, max_retries: int = 1) -> Univ3SubgraphClient:
    return Univ3SubgraphClient(
        Univ3SubgraphClientSettings(
            graph_gateway_base="https://gateway.thegraph.com/api",
            graph_api_key="api-key",
            graph_subgraph_ids={"ethereum": "subgraph-id"},
            graph_blocks_subgraph_ids={"ethereum": "blocks-id"},
            timeout_seconds=10,
            max_retries=max_retries,
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


def _ticks_payload(start: int, end: int, *, meta_block: int | None) -> dict:
    rows = [
        {
            "tickIdx": str(tick),
            "liquidityGross": "10",
            "liquidityNet": "1",
            "price0": "1",
            "price1": "1",
            "feeGrowthOutside0X128": "0",
            "feeGrowthOutside1X128": "0",
        }
        for tick in range(start, end + 1)
    ]
    return {
        "data": {
            "ticks": rows,
            "_meta": {"block": {"number": meta_block} if meta_block is not None else None},
        }
    }


def test_fetch_initialized_ticks_retries_full_pagination_when_meta_block_drifts(monkeypatch: pytest.MonkeyPatch):
    client = _make_client(max_retries=2)
    monkeypatch.setattr(
        "app.infrastructure.clients.univ3_subgraph_client.time.sleep",
        lambda _seconds: None,
    )

    scripted_payloads = [
        _ticks_payload(1, 1000, meta_block=100),   # attempt 1 / page 1
        _ticks_payload(1001, 2000, meta_block=90), # attempt 1 / page 2 -> drift
        _ticks_payload(1, 1000, meta_block=200),   # attempt 2 / page 1
        _ticks_payload(1001, 2000, meta_block=200),# attempt 2 / page 2
        {"data": {"ticks": [], "_meta": {"block": {"number": 200}}}},  # attempt 2 / page 3 (end)
    ]
    expected_last_ticks = [-1, 1000, -1, 1000, 2000]
    state = {"idx": 0}

    def fake_post_graphql(*, url: str, query: str, variables: dict) -> dict:
        _ = (url, query)
        idx = state["idx"]
        assert variables["lastTick"] == expected_last_ticks[idx]
        payload = scripted_payloads[idx]
        state["idx"] = idx + 1
        return payload

    monkeypatch.setattr(client, "_post_graphql", fake_post_graphql)

    rows = client.fetch_initialized_ticks(
        pool_address="0xabc",
        chain_id=1,
        min_tick=0,
        max_tick=5000,
    )

    assert len(rows) == 2000
    assert state["idx"] == 5
    assert all(row.updated_at_block == 200 for row in rows)


class _FakeBegin:
    def __init__(self, engine: "_FakeEngine"):
        self._engine = engine

    def __enter__(self) -> "_FakeEngine":
        return self._engine

    def __exit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)
        return None


class _FakeEngine:
    def __init__(self):
        self.sql: str | None = None
        self.params: list[dict] | None = None

    def begin(self) -> _FakeBegin:
        return _FakeBegin(self)

    def execute(self, sql, params):  # pragma: no cover - simple capture helper
        self.sql = str(sql)
        self.params = params
        return None


def test_upsert_initialized_ticks_sql_has_block_freshness_where_when_column_exists(monkeypatch: pytest.MonkeyPatch):
    engine = _FakeEngine()
    repo = SqlTickSnapshotOnDemandRepository(engine, subgraph_client=None)  # type: ignore[arg-type]
    monkeypatch.setattr(
        repo,
        "_get_pool_ticks_initialized_columns",
        lambda: {
            "dex_id",
            "chain_id",
            "pool_address",
            "tick_idx",
            "liquidity_net",
            "updated_at_block",
            "updated_at",
        },
    )

    repo.upsert_initialized_ticks(
        pool_address="0xABC",
        chain_id=1,
        dex_id=2,
        rows=[InitializedTickSourceRow(tick_idx=10, liquidity_net="1", updated_at_block=123)],
    )

    assert engine.sql is not None
    assert "WHERE public.pool_ticks_initialized.updated_at_block IS NULL" in engine.sql
    assert "EXCLUDED.updated_at_block >= public.pool_ticks_initialized.updated_at_block" in engine.sql
