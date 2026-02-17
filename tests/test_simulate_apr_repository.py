from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
import unittest

from app.infrastructure.db.mappers.simulate_apr_mapper import map_row_to_simulate_apr_snapshot_hourly


class SimulateAprRepositoryTests(unittest.TestCase):
    def test_mapper_maps_snapshot_tick_and_liquidity(self):
        row = {
            "hour_ts": datetime(2026, 2, 1, 10, 0, 0),
            "tick": -200000,
            "liquidity": "12345.67",
        }
        mapped = map_row_to_simulate_apr_snapshot_hourly(row)
        self.assertEqual(mapped.tick, -200000)
        self.assertEqual(mapped.liquidity, Decimal("12345.67"))

    def test_repository_query_uses_utc_hour_bucket_and_selects_liquidity(self):
        source = Path("app/infrastructure/db/repositories/simulate_apr_repository.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "date_trunc('hour', to_timestamp(s.meta_block_timestamp) AT TIME ZONE 'UTC') AS hour_ts",
            source,
        )
        self.assertIn(
            "PARTITION BY date_trunc('hour', to_timestamp(s.meta_block_timestamp) AT TIME ZONE 'UTC')",
            source,
        )
        self.assertIn("(now() AT TIME ZONE 'UTC') - (:hours || ' hours')::interval", source)
        self.assertIn("SELECT hour_ts, tick, liquidity", source)


if __name__ == "__main__":
    unittest.main()
