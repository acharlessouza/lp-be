from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.dto.simulate_apr_v2 import SimulateAprV2Input
from app.application.dto.tick_snapshot_on_demand import MissingTickSnapshot, TickSnapshotUpsertRow
from app.application.use_cases.simulate_apr_v2 import SimulateAprV2UseCase
from app.domain.entities.simulate_apr import SimulateAprInitializedTick
from app.domain.entities.simulate_apr_v2 import (
    SimulateAprV2Pool,
    SimulateAprV2PoolSnapshot,
    SimulateAprV2TickSnapshot,
)
from app.domain.exceptions import SimulationDataNotFoundError


class FakeSimulateAprV2Port:
    def __init__(self, *, lookback_exists: bool = True):
        self.lookback_exists = lookback_exists
        self._rows = {
            (100, -10): SimulateAprV2TickSnapshot(
                block_number=100,
                tick_idx=-10,
                fee_growth_outside0_x128="100",
                fee_growth_outside1_x128="200",
                liquidity_net=None,
                liquidity_gross=None,
            ),
            (100, 10): SimulateAprV2TickSnapshot(
                block_number=100,
                tick_idx=10,
                fee_growth_outside0_x128="150",
                fee_growth_outside1_x128="250",
                liquidity_net=None,
                liquidity_gross=None,
            ),
            (200, -10): SimulateAprV2TickSnapshot(
                block_number=200,
                tick_idx=-10,
                fee_growth_outside0_x128="120",
                fee_growth_outside1_x128="230",
                liquidity_net=None,
                liquidity_gross=None,
            ),
            (200, 10): SimulateAprV2TickSnapshot(
                block_number=200,
                tick_idx=10,
                fee_growth_outside0_x128="170",
                fee_growth_outside1_x128="260",
                liquidity_net=None,
                liquidity_gross=None,
            ),
        }

    def drop_tick_snapshot(self, *, block_number: int, tick_idx: int) -> None:
        self._rows.pop((block_number, tick_idx), None)

    def add_tick_snapshot(self, row: TickSnapshotUpsertRow) -> None:
        self._rows[(row.block_number, row.tick_idx)] = SimulateAprV2TickSnapshot(
            block_number=row.block_number,
            tick_idx=row.tick_idx,
            fee_growth_outside0_x128=row.fee_growth_outside0_x128,
            fee_growth_outside1_x128=row.fee_growth_outside1_x128,
            liquidity_net=None,
            liquidity_gross=None,
        )

    def get_pool(self, *, pool_address: str, chain_id: int, dex_id: int) -> SimulateAprV2Pool | None:
        _ = (pool_address, chain_id, dex_id)
        return SimulateAprV2Pool(
            dex_id=2,
            chain_id=1,
            pool_address="0xpool",
            token0_decimals=0,
            token1_decimals=0,
            fee_tier=3000,
            tick_spacing=10,
        )

    def get_latest_pool_snapshot(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
    ) -> SimulateAprV2PoolSnapshot | None:
        _ = (pool_address, chain_id, dex_id)
        return SimulateAprV2PoolSnapshot(
            block_number=200,
            block_timestamp=186400,
            tick=5,
            sqrt_price_x96=None,
            liquidity=Decimal("1000"),
            fee_growth_global0_x128="1000",
            fee_growth_global1_x128="2000",
        )

    def get_lookback_pool_snapshot(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        target_timestamp: int,
    ) -> SimulateAprV2PoolSnapshot | None:
        _ = (pool_address, chain_id, dex_id, target_timestamp)
        if not self.lookback_exists:
            return None
        return SimulateAprV2PoolSnapshot(
            block_number=100,
            block_timestamp=100000,
            tick=0,
            sqrt_price_x96=None,
            liquidity=Decimal("900"),
            fee_growth_global0_x128="700",
            fee_growth_global1_x128="1300",
        )

    def get_tick_snapshots_for_blocks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> list[SimulateAprV2TickSnapshot]:
        _ = (pool_address, chain_id, dex_id)
        result: list[SimulateAprV2TickSnapshot] = []
        for block in block_numbers:
            for tick in tick_indices:
                row = self._rows.get((block, tick))
                if row is not None:
                    result.append(row)
        return result

    def get_initialized_ticks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        min_tick: int,
        max_tick: int,
    ) -> list[SimulateAprInitializedTick]:
        _ = (pool_address, chain_id, dex_id, min_tick, max_tick)
        return [
            SimulateAprInitializedTick(tick_idx=-10, liquidity_net=Decimal("100")),
            SimulateAprInitializedTick(tick_idx=10, liquidity_net=Decimal("-100")),
        ]


class FakeTickSnapshotOnDemandPort:
    def __init__(
        self,
        *,
        apr_port: FakeSimulateAprV2Port,
        return_empty_fetch: bool = False,
        raise_fetch_error: RuntimeError | None = None,
    ):
        self._apr_port = apr_port
        self.return_empty_fetch = return_empty_fetch
        self.raise_fetch_error = raise_fetch_error

    def get_missing_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> list[MissingTickSnapshot]:
        existing = {
            (row.block_number, row.tick_idx)
            for row in self._apr_port.get_tick_snapshots_for_blocks(
                pool_address=pool_address,
                chain_id=chain_id,
                dex_id=dex_id,
                block_numbers=block_numbers,
                tick_indices=tick_indices,
            )
        }
        expected = {(block, tick) for block in block_numbers for tick in tick_indices}
        missing = sorted(expected - existing)
        return [MissingTickSnapshot(block_number=block, tick_idx=tick) for block, tick in missing]

    def fetch_tick_snapshots(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        combinations: list[MissingTickSnapshot],
    ) -> list[TickSnapshotUpsertRow]:
        _ = (pool_address, chain_id, dex_id)
        if self.raise_fetch_error is not None:
            raise self.raise_fetch_error
        if self.return_empty_fetch:
            return []

        rows: list[TickSnapshotUpsertRow] = []
        for combo in combinations:
            rows.append(
                TickSnapshotUpsertRow(
                    dex_id=dex_id,
                    chain_id=chain_id,
                    pool_address=pool_address.lower(),
                    block_number=combo.block_number,
                    tick_idx=combo.tick_idx,
                    fee_growth_outside0_x128="111",
                    fee_growth_outside1_x128="222",
                )
            )
        return rows

    def upsert_tick_snapshots(self, *, rows: list[TickSnapshotUpsertRow]) -> int:
        for row in rows:
            self._apr_port.add_tick_snapshot(row)
        return len(rows)

    def fetch_blocks_metadata(self, *, chain_id: int, block_numbers: list[int]):
        _ = (chain_id, block_numbers)
        return []

    def upsert_blocks(self, *, rows: list):
        _ = rows
        return 0


@pytest.fixture
def base_input() -> SimulateAprV2Input:
    return SimulateAprV2Input(
        pool_address="0xpool",
        chain_id=1,
        dex_id=2,
        deposit_usd=Decimal("100"),
        amount_token0=Decimal("1"),
        amount_token1=Decimal("1"),
        full_range=False,
        tick_lower=-10,
        tick_upper=10,
        min_price=None,
        max_price=None,
        horizon="24h",
        lookback_days=1,
        calculation_method="custom",
        custom_calculation_price=Decimal("2"),
        apr_method="exact",
    )


def _make_use_case(
    *,
    apr_port: FakeSimulateAprV2Port,
    on_demand_port: FakeTickSnapshotOnDemandPort,
) -> SimulateAprV2UseCase:
    return SimulateAprV2UseCase(
        simulate_apr_v2_port=apr_port,
        tick_snapshot_on_demand_port=on_demand_port,
    )


def test_execute_happy_path_annualizes_with_seconds_delta(monkeypatch: pytest.MonkeyPatch, base_input: SimulateAprV2Input):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )
    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    result = use_case.execute(base_input)

    q128 = Decimal(2**128)
    expected_period = (Decimal("10") * Decimal("1180")) / q128
    assert result.estimated_fees_period_usd == expected_period
    assert result.estimated_fees_24h_usd == expected_period
    assert result.yearly_usd == expected_period * Decimal("365")
    assert result.monthly_usd == (expected_period * Decimal("365")) / Decimal("12")
    assert result.fee_apr == (expected_period * Decimal("365")) / Decimal("100")
    assert result.meta.seconds_delta == 86400
    assert result.meta.block_a_number == 100
    assert result.meta.block_b_number == 200


def test_execute_raises_when_lookback_snapshot_is_missing(base_input: SimulateAprV2Input):
    apr_port = FakeSimulateAprV2Port(lookback_exists=False)
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    with pytest.raises(SimulationDataNotFoundError):
        use_case.execute(base_input)


def test_execute_when_tick_missing_runs_on_demand_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )
    apr_port = FakeSimulateAprV2Port()
    apr_port.drop_tick_snapshot(block_number=100, tick_idx=10)

    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    result = use_case.execute(base_input)

    assert result.estimated_fees_period_usd > Decimal("0")


def test_execute_raises_when_on_demand_still_missing(base_input: SimulateAprV2Input):
    apr_port = FakeSimulateAprV2Port()
    apr_port.drop_tick_snapshot(block_number=100, tick_idx=10)

    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            return_empty_fetch=True,
        ),
    )

    with pytest.raises(SimulationDataNotFoundError) as exc:
        use_case.execute(base_input)

    assert "Missing tick snapshots" in str(exc.value)


def test_execute_raises_when_subgraph_does_not_support_block(base_input: SimulateAprV2Input):
    apr_port = FakeSimulateAprV2Port()
    apr_port.drop_tick_snapshot(block_number=100, tick_idx=10)

    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            raise_fetch_error=RuntimeError("Subgraph nao suporta argumento block."),
        ),
    )

    with pytest.raises(SimulationDataNotFoundError) as exc:
        use_case.execute(base_input)

    assert "Falha no on-demand do subgraph" in str(exc.value)
