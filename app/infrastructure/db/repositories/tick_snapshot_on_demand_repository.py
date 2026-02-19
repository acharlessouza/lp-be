from __future__ import annotations

import logging
from time import perf_counter

from sqlalchemy import bindparam, text

from app.application.dto.tick_snapshot_on_demand import (
    BlockUpsertRow,
    MissingTickSnapshot,
    TickSnapshotUpsertRow,
)
from app.application.ports.tick_snapshot_on_demand_port import TickSnapshotOnDemandPort
from app.infrastructure.clients.univ3_subgraph_client import Univ3SubgraphClient


logger = logging.getLogger(__name__)


class SqlTickSnapshotOnDemandRepository(TickSnapshotOnDemandPort):
    def __init__(self, engine, *, subgraph_client: Univ3SubgraphClient):
        self._engine = engine
        self._subgraph_client = subgraph_client
        self._tick_snapshot_columns: set[str] | None = None
        self._blocks_columns: set[str] | None = None

    def get_missing_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> list[MissingTickSnapshot]:
        unique_blocks = sorted(set(block_numbers))
        unique_ticks = sorted(set(tick_indices))
        if not unique_blocks or not unique_ticks:
            return []

        sql = text(
            """
            SELECT block_number, tick_idx
            FROM apr_exact.tick_snapshot
            WHERE dex_id = :dex_id
              AND chain_id = :chain_id
              AND lower(pool_address) = :pool_address
              AND block_number IN :block_numbers
              AND tick_idx IN :tick_indices
            """
        ).bindparams(
            bindparam("block_numbers", expanding=True),
            bindparam("tick_indices", expanding=True),
        )

        with self._engine.connect() as conn:
            rows = conn.execute(
                sql,
                {
                    "dex_id": dex_id,
                    "chain_id": chain_id,
                    "pool_address": pool_address.lower(),
                    "block_numbers": unique_blocks,
                    "tick_indices": unique_ticks,
                },
            ).mappings().all()

        existing = {(int(row["block_number"]), int(row["tick_idx"])) for row in rows}
        expected = {(block, tick) for block in unique_blocks for tick in unique_ticks}
        missing = sorted(expected - existing)
        result = [MissingTickSnapshot(block_number=block, tick_idx=tick) for block, tick in missing]

        logger.info(
            "tick_snapshot_on_demand_repo: missing_check pool=%s chain_id=%s dex_id=%s expected=%s found=%s missing=%s",
            pool_address.lower(),
            chain_id,
            dex_id,
            len(expected),
            len(existing),
            len(result),
        )
        return result

    def fetch_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        combinations: list[MissingTickSnapshot],
    ) -> list[TickSnapshotUpsertRow]:
        start = perf_counter()
        rows = self._subgraph_client.fetch_tick_snapshots(
            pool_address=pool_address,
            chain_id=chain_id,
            dex_id=dex_id,
            combinations=combinations,
        )
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(
            "tick_snapshot_on_demand_repo: fetched_from_source requested=%s fetched=%s elapsed_ms=%.2f",
            len(combinations),
            len(rows),
            elapsed_ms,
        )
        return rows

    def upsert_tick_snapshots(self, *, rows: list[TickSnapshotUpsertRow]) -> int:
        if not rows:
            return 0

        columns = self._get_tick_snapshot_columns()
        base_columns = [
            "dex_id",
            "chain_id",
            "pool_address",
            "block_number",
            "tick_idx",
            "fee_growth_outside0_x128",
            "fee_growth_outside1_x128",
        ]
        optional_columns = []
        if "liquidity_gross" in columns:
            optional_columns.append("liquidity_gross")
        if "liquidity_net" in columns:
            optional_columns.append("liquidity_net")

        all_columns = base_columns + optional_columns

        values_clause = ", ".join(f":{col}" for col in all_columns)
        insert_columns = ", ".join(all_columns)

        updates = [
            "fee_growth_outside0_x128 = EXCLUDED.fee_growth_outside0_x128",
            "fee_growth_outside1_x128 = EXCLUDED.fee_growth_outside1_x128",
        ]
        if "liquidity_gross" in optional_columns:
            updates.append("liquidity_gross = EXCLUDED.liquidity_gross")
        if "liquidity_net" in optional_columns:
            updates.append("liquidity_net = EXCLUDED.liquidity_net")

        sql = text(
            f"""
            INSERT INTO apr_exact.tick_snapshot ({insert_columns})
            VALUES ({values_clause})
            ON CONFLICT (chain_id, dex_id, pool_address, tick_idx, block_number)
            DO UPDATE SET {", ".join(updates)}
            """
        )

        params = []
        for row in rows:
            item = {
                "dex_id": row.dex_id,
                "chain_id": row.chain_id,
                "pool_address": row.pool_address.lower(),
                "block_number": row.block_number,
                "tick_idx": row.tick_idx,
                "fee_growth_outside0_x128": row.fee_growth_outside0_x128,
                "fee_growth_outside1_x128": row.fee_growth_outside1_x128,
            }
            if "liquidity_gross" in optional_columns:
                item["liquidity_gross"] = row.liquidity_gross
            if "liquidity_net" in optional_columns:
                item["liquidity_net"] = row.liquidity_net
            params.append(item)

        with self._engine.begin() as conn:
            conn.execute(sql, params)

        logger.info("tick_snapshot_on_demand_repo: upsert_tick_snapshots rows=%s", len(rows))
        return len(rows)

    def fetch_blocks_metadata(
        self,
        *,
        chain_id: int,
        block_numbers: list[int],
    ) -> list[BlockUpsertRow]:
        return self._subgraph_client.fetch_blocks(chain_id=chain_id, block_numbers=block_numbers)

    def upsert_blocks(self, *, rows: list[BlockUpsertRow]) -> int:
        if not rows:
            return 0

        columns = self._get_blocks_columns()
        if not columns:
            logger.info("tick_snapshot_on_demand_repo: apr_exact.blocks not found, skip upsert")
            return 0

        number_col = "number" if "number" in columns else "block_number" if "block_number" in columns else None
        ts_col = "timestamp" if "timestamp" in columns else "block_timestamp" if "block_timestamp" in columns else None
        if number_col is None or ts_col is None:
            logger.info(
                "tick_snapshot_on_demand_repo: apr_exact.blocks missing expected columns, skip upsert columns=%s",
                sorted(columns),
            )
            return 0

        sql = text(
            f"""
            INSERT INTO apr_exact.blocks (chain_id, {number_col}, {ts_col})
            VALUES (:chain_id, :block_number, :timestamp)
            ON CONFLICT (chain_id, {number_col})
            DO UPDATE SET {ts_col} = EXCLUDED.{ts_col}
            """
        )

        params = [
            {
                "chain_id": row.chain_id,
                "block_number": row.block_number,
                "timestamp": row.timestamp,
            }
            for row in rows
        ]

        with self._engine.begin() as conn:
            conn.execute(sql, params)

        logger.info("tick_snapshot_on_demand_repo: upsert_blocks rows=%s", len(rows))
        return len(rows)

    def _get_tick_snapshot_columns(self) -> set[str]:
        if self._tick_snapshot_columns is not None:
            return self._tick_snapshot_columns

        sql = text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'apr_exact'
              AND table_name = 'tick_snapshot'
            """
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql).mappings().all()

        self._tick_snapshot_columns = {str(row["column_name"]) for row in rows}
        return self._tick_snapshot_columns

    def _get_blocks_columns(self) -> set[str]:
        if self._blocks_columns is not None:
            return self._blocks_columns

        sql = text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'apr_exact'
              AND table_name = 'blocks'
            """
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql).mappings().all()

        self._blocks_columns = {str(row["column_name"]) for row in rows}
        return self._blocks_columns
