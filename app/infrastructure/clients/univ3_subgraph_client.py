from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import Lock
import time

import httpx

from app.application.dto.tick_snapshot_on_demand import BlockUpsertRow, MissingTickSnapshot, TickSnapshotUpsertRow


logger = logging.getLogger(__name__)


CHAIN_ID_TO_KEY = {
    1: "ethereum",
    42161: "arbitrum",
    8453: "base",
    137: "polygon",
    56: "bsc",
}


class SubgraphBlockNotSupportedError(RuntimeError):
    pass


class SubgraphResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Univ3SubgraphClientSettings:
    graph_gateway_base: str
    graph_api_key: str
    graph_subgraph_ids: dict
    graph_blocks_subgraph_ids: dict
    timeout_seconds: float
    max_retries: int
    min_interval_ms: int


class Univ3SubgraphClient:
    def __init__(self, settings: Univ3SubgraphClientSettings):
        self._settings = settings
        self._lock = Lock()
        self._last_request_at = 0.0

    def fetch_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        combinations: list[MissingTickSnapshot],
    ) -> list[TickSnapshotUpsertRow]:
        if not combinations:
            return []

        subgraph_url = self._resolve_subgraph_url(chain_id)
        pool_id = pool_address.lower()

        rows: list[TickSnapshotUpsertRow] = []
        for combo in combinations:
            tick_row = self._fetch_tick_at_block(
                subgraph_url=subgraph_url,
                pool_id=pool_id,
                tick_idx=combo.tick_idx,
                block_number=combo.block_number,
            )
            if tick_row is None:
                continue

            rows.append(
                TickSnapshotUpsertRow(
                    dex_id=dex_id,
                    chain_id=chain_id,
                    pool_address=pool_id,
                    block_number=combo.block_number,
                    tick_idx=int(tick_row["tickIdx"]),
                    liquidity_gross=tick_row.get("liquidityGross"),
                    liquidity_net=tick_row.get("liquidityNet"),
                    fee_growth_outside0_x128=tick_row.get("feeGrowthOutside0X128"),
                    fee_growth_outside1_x128=tick_row.get("feeGrowthOutside1X128"),
                )
            )

        logger.info(
            "univ3_subgraph_client: fetched_tick_snapshots requested=%s fetched=%s pool=%s chain_id=%s dex_id=%s",
            len(combinations),
            len(rows),
            pool_id,
            chain_id,
            dex_id,
        )
        return rows

    def fetch_blocks(
        self,
        *,
        chain_id: int,
        block_numbers: list[int],
    ) -> list[BlockUpsertRow]:
        unique_numbers = sorted(set(block_numbers))
        if not unique_numbers:
            return []

        blocks_url = self._resolve_blocks_subgraph_url(chain_id)
        if not blocks_url:
            logger.info(
                "univ3_subgraph_client: blocks_subgraph_not_configured chain_id=%s",
                chain_id,
            )
            return []

        query = """
        query BlocksByNumber($numbers: [Int!]!) {
          blocks(where: { number_in: $numbers }) {
            number
            timestamp
          }
        }
        """
        payload = self._post_graphql(
            url=blocks_url,
            query=query,
            variables={"numbers": unique_numbers},
        )
        rows = payload.get("data", {}).get("blocks") or []
        mapped: list[BlockUpsertRow] = []
        for row in rows:
            number = row.get("number")
            timestamp = row.get("timestamp")
            if number is None or timestamp is None:
                continue
            mapped.append(
                BlockUpsertRow(
                    chain_id=chain_id,
                    block_number=int(number),
                    timestamp=int(timestamp),
                )
            )

        logger.info(
            "univ3_subgraph_client: fetched_blocks requested=%s fetched=%s chain_id=%s",
            len(unique_numbers),
            len(mapped),
            chain_id,
        )
        return mapped

    def _fetch_tick_at_block(
        self,
        *,
        subgraph_url: str,
        pool_id: str,
        tick_idx: int,
        block_number: int,
    ) -> dict | None:
        tick_id = f"{pool_id}#{tick_idx}"

        query_by_id = """
        query TickAtBlockById($id: ID!, $block: Int!) {
          tick(id: $id, block: { number: $block }) {
            tickIdx
            liquidityGross
            liquidityNet
            feeGrowthOutside0X128
            feeGrowthOutside1X128
          }
        }
        """

        query_by_where = """
        query TickAtBlockByWhere($poolId: ID!, $tick: Int!, $block: Int!) {
          ticks(first: 1, where: { pool: $poolId, tickIdx: $tick }, block: { number: $block }) {
            tickIdx
            liquidityGross
            liquidityNet
            feeGrowthOutside0X128
            feeGrowthOutside1X128
          }
        }
        """

        errors: list[str] = []

        try:
            payload = self._post_graphql(
                url=subgraph_url,
                query=query_by_id,
                variables={"id": tick_id, "block": block_number},
            )
            tick = payload.get("data", {}).get("tick")
            if tick:
                return tick
            return None
        except SubgraphBlockNotSupportedError:
            raise
        except RuntimeError as exc:
            errors.append(f"by_id:{exc}")

        try:
            payload = self._post_graphql(
                url=subgraph_url,
                query=query_by_where,
                variables={"poolId": pool_id, "tick": tick_idx, "block": block_number},
            )
            ticks = payload.get("data", {}).get("ticks") or []
            if ticks:
                return ticks[0]
            return None
        except SubgraphBlockNotSupportedError:
            raise
        except RuntimeError as exc:
            errors.append(f"by_where:{exc}")

        if errors:
            raise RuntimeError("; ".join(errors))
        return None

    def _post_graphql(self, *, url: str, query: str, variables: dict) -> dict:
        attempts = max(1, self._settings.max_retries)
        delay = 0.25
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            self._respect_rate_limit()
            try:
                with httpx.Client(timeout=self._settings.timeout_seconds) as client:
                    response = client.post(
                        url,
                        json={"query": query, "variables": variables},
                    )
                    response.raise_for_status()
                    payload = response.json()

                errors = payload.get("errors") or []
                if errors:
                    message = " | ".join(str(err.get("message", err)) for err in errors)
                    lower_msg = message.lower()
                    if "unknown argument \"block\"" in lower_msg or "argument \"block\"" in lower_msg:
                        raise SubgraphBlockNotSupportedError(
                            "Subgraph nao suporta consultas com argumento block para o metodo exato."
                        )
                    raise RuntimeError(message)

                return payload
            except SubgraphBlockNotSupportedError:
                raise
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                last_exc = exc
                if attempt == attempts:
                    break
                logger.warning(
                    "univ3_subgraph_client: graphql_retry attempt=%s/%s error=%s",
                    attempt,
                    attempts,
                    exc,
                )
                time.sleep(delay)
                delay *= 2

        raise RuntimeError(f"GraphQL request failed after retries: {last_exc}") from last_exc

    def _respect_rate_limit(self) -> None:
        min_interval = max(0, self._settings.min_interval_ms) / 1000.0
        if min_interval <= 0:
            return

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_at
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_at = time.monotonic()

    def _resolve_subgraph_url(self, chain_id: int) -> str:
        chain_key = CHAIN_ID_TO_KEY.get(chain_id)
        if not chain_key:
            raise SubgraphResolutionError(f"Unsupported chain_id for subgraph resolution: {chain_id}")

        subgraph_id = str(self._settings.graph_subgraph_ids.get(chain_key) or "").strip()
        if not subgraph_id:
            raise SubgraphResolutionError(
                f"Missing GRAPH_SUBGRAPH_ID for chain '{chain_key}' (chain_id={chain_id})."
            )
        return self._build_gateway_url(subgraph_id)

    def _resolve_blocks_subgraph_url(self, chain_id: int) -> str | None:
        chain_key = CHAIN_ID_TO_KEY.get(chain_id)
        if not chain_key:
            return None

        subgraph_id = str(self._settings.graph_blocks_subgraph_ids.get(chain_key) or "").strip()
        if not subgraph_id:
            return None
        return self._build_gateway_url(subgraph_id)

    def _build_gateway_url(self, subgraph_id: str) -> str:
        base = self._settings.graph_gateway_base.rstrip("/")
        api_key = self._settings.graph_api_key.strip()
        if api_key:
            return f"{base}/{api_key}/subgraphs/id/{subgraph_id}"
        return f"{base}/subgraphs/id/{subgraph_id}"
