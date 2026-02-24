from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.application.dto.simulate_apr_v2 import SimulateAprV2Input
from app.application.dto.tick_snapshot_on_demand import (
    InitializedTickSourceRow,
    MissingTickSnapshot,
    TickSnapshotUpsertRow,
)
from app.application.use_cases.simulate_apr_v2 import (
    UNISWAP_V3_MAX_TICK,
    UNISWAP_V3_MIN_TICK,
    SimulateAprV2UseCase,
)
from app.domain.entities.simulate_apr import SimulateAprInitializedTick
from app.domain.entities.simulate_apr_v2 import (
    SimulateAprV2Pool,
    SimulateAprV2PoolSnapshot,
    SimulateAprV2TickSnapshot,
)
from app.domain.exceptions import SimulationDataNotFoundError


class FakeSimulateAprV2Port:
    def __init__(
        self,
        *,
        lookback_exists: bool = True,
        initialized_ticks: list[SimulateAprInitializedTick] | None = None,
    ):
        self.lookback_exists = lookback_exists
        if initialized_ticks is None:
            initialized_ticks = [
                SimulateAprInitializedTick(tick_idx=-10, liquidity_net=Decimal("100")),
                SimulateAprInitializedTick(tick_idx=10, liquidity_net=Decimal("-100")),
            ]
        self.initialized_ticks = initialized_ticks
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
        return self.initialized_ticks


class FakeTickSnapshotOnDemandPort:
    def __init__(
        self,
        *,
        apr_port: FakeSimulateAprV2Port,
        return_empty_fetch: bool = False,
        raise_fetch_error: RuntimeError | None = None,
        initialized_ticks_rows: list[InitializedTickSourceRow] | None = None,
        raise_initialized_ticks_fetch_error: RuntimeError | None = None,
    ):
        self._apr_port = apr_port
        self.return_empty_fetch = return_empty_fetch
        self.raise_fetch_error = raise_fetch_error
        self.initialized_ticks_rows = initialized_ticks_rows or []
        self.raise_initialized_ticks_fetch_error = raise_initialized_ticks_fetch_error
        self.initialized_ticks_upsert_count = 0

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

    def fetch_initialized_ticks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        min_tick: int,
        max_tick: int,
    ) -> list[InitializedTickSourceRow]:
        _ = (pool_address, chain_id, dex_id, min_tick, max_tick)
        if self.raise_initialized_ticks_fetch_error is not None:
            raise self.raise_initialized_ticks_fetch_error
        return self.initialized_ticks_rows

    def upsert_initialized_ticks(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        rows: list[InitializedTickSourceRow],
    ) -> int:
        _ = (pool_address, chain_id, dex_id)
        self.initialized_ticks_upsert_count += len(rows)
        return len(rows)


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
    assert abs(result.estimated_fees_period_usd - expected_period) <= Decimal("1e-80")
    assert abs(result.estimated_fees_24h_usd - expected_period) <= Decimal("1e-80")
    assert abs(result.yearly_usd - (expected_period * Decimal("365"))) <= Decimal("1e-80")
    assert abs(result.monthly_usd - ((expected_period * Decimal("365")) / Decimal("12"))) <= Decimal("1e-80")
    assert abs(result.fee_apr - ((expected_period * Decimal("365")) / Decimal("100"))) <= Decimal("1e-80")
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

    assert exc.value.code == "tick_snapshots_missing_after_on_demand"
    assert "missing" in exc.value.context


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

    assert exc.value.code == "tick_snapshots_on_demand_failed"
    assert "error" in exc.value.context


def test_execute_swapped_pair_converts_input_and_returns_used_price_ui(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    captured: dict[str, Decimal] = {}

    def _capture_position_liquidity_v3(**kwargs):
        captured["amount_token0"] = kwargs["amount_token0"]
        captured["amount_token1"] = kwargs["amount_token1"]
        return Decimal("10")

    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        _capture_position_liquidity_v3,
    )
    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    result = use_case.execute(
        replace(
            base_input,
            tick_lower=-20,
            tick_upper=-10,
            amount_token0=Decimal("1"),
            amount_token1=Decimal("3"),
            custom_calculation_price=Decimal("4"),
            swapped_pair=True,
        )
    )

    assert captured["amount_token0"] == Decimal("3")
    assert captured["amount_token1"] == Decimal("1")
    assert result.meta.used_price == Decimal("4")


def test_execute_fetches_initialized_ticks_on_demand_when_db_missing(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )
    apr_port = FakeSimulateAprV2Port(initialized_ticks=[])
    on_demand_port = FakeTickSnapshotOnDemandPort(
        apr_port=apr_port,
        initialized_ticks_rows=[
            InitializedTickSourceRow(tick_idx=-10, liquidity_net="100"),
            InitializedTickSourceRow(tick_idx=10, liquidity_net="-100"),
        ],
    )
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=on_demand_port,
    )

    result = use_case.execute(
        replace(
            base_input,
            calculation_method="avg_liquidity_in_range",
            custom_calculation_price=None,
        )
    )

    assert result.estimated_fees_period_usd > Decimal("0")
    assert on_demand_port.initialized_ticks_upsert_count == 2


def test_execute_raises_when_initialized_ticks_on_demand_fails(
    base_input: SimulateAprV2Input,
):
    apr_port = FakeSimulateAprV2Port(initialized_ticks=[])
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            raise_initialized_ticks_fetch_error=RuntimeError("timeout on subgraph"),
        ),
    )

    with pytest.raises(SimulationDataNotFoundError) as exc:
        use_case.execute(
            replace(
                base_input,
                calculation_method="avg_liquidity_in_range",
                custom_calculation_price=None,
            )
        )

    assert exc.value.code == "initialized_ticks_on_demand_failed"
    assert "error" in exc.value.context


def test_execute_price_range_without_ticks_swapped_false_uses_price_path(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    captured: dict[str, Decimal] = {}

    def _floor(price: Decimal, *_args):
        captured["floor_price"] = price
        return -10

    def _ceil(price: Decimal, *_args):
        captured["ceil_price"] = price
        return 10

    monkeypatch.setattr("app.application.use_cases.simulate_apr_v2.price_to_tick_floor", _floor)
    monkeypatch.setattr("app.application.use_cases.simulate_apr_v2.price_to_tick_ceil", _ceil)
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )

    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    result = use_case.execute(
        replace(
            base_input,
            tick_lower=None,
            tick_upper=None,
            min_price=Decimal("1"),
            max_price=Decimal("2"),
            swapped_pair=False,
            calculation_method="custom",
            custom_calculation_price=Decimal("2"),
        )
    )

    assert result.estimated_fees_period_usd > Decimal("0")
    assert captured["floor_price"] == Decimal("1")
    assert captured["ceil_price"] == Decimal("2")


def test_execute_price_range_without_ticks_swapped_true_uses_canonical_prices(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    captured: dict[str, Decimal] = {}

    def _floor(price: Decimal, *_args):
        captured["floor_price"] = price
        return -10

    def _ceil(price: Decimal, *_args):
        captured["ceil_price"] = price
        return 10

    monkeypatch.setattr("app.application.use_cases.simulate_apr_v2.price_to_tick_floor", _floor)
    monkeypatch.setattr("app.application.use_cases.simulate_apr_v2.price_to_tick_ceil", _ceil)
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )

    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    result = use_case.execute(
        replace(
            base_input,
            tick_lower=None,
            tick_upper=None,
            min_price=Decimal("0.5"),
            max_price=Decimal("1"),
            swapped_pair=True,
            calculation_method="custom",
            custom_calculation_price=Decimal("0.5"),
        )
    )

    assert result.estimated_fees_period_usd > Decimal("0")
    assert captured["floor_price"] == Decimal("1")
    assert captured["ceil_price"] == Decimal("2")


def test_execute_initialized_ticks_not_found_exposes_code_and_context(
    base_input: SimulateAprV2Input,
):
    apr_port = FakeSimulateAprV2Port(initialized_ticks=[])
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            initialized_ticks_rows=[],
        ),
    )

    with pytest.raises(SimulationDataNotFoundError) as exc:
        use_case.execute(
            replace(
                base_input,
                calculation_method="avg_liquidity_in_range",
                custom_calculation_price=None,
                swapped_pair=True,
            )
        )

    assert exc.value.code == "initialized_ticks_not_found"
    assert exc.value.context["swapped_pair_input"] is True
    assert exc.value.context["canonicalized"] is True
    assert exc.value.context["tick_lower"] == -10
    assert exc.value.context["tick_upper"] == 10


def test_execute_price_range_exact_adjusts_boundaries_to_initialized_ticks(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.price_to_tick_floor",
        lambda *_args: -11,
    )
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.price_to_tick_ceil",
        lambda *_args: 11,
    )

    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            return_empty_fetch=True,
        ),
    )

    result = use_case.execute(
        replace(
            base_input,
            tick_lower=None,
            tick_upper=None,
            min_price=Decimal("1"),
            max_price=Decimal("2"),
            calculation_method="custom",
            custom_calculation_price=Decimal("2"),
        )
    )

    assert result.estimated_fees_period_usd > Decimal("0")


def test_execute_price_range_exact_raises_specific_error_when_boundaries_not_snapshotable(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.price_to_tick_floor",
        lambda *_args: -11,
    )
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.price_to_tick_ceil",
        lambda *_args: 11,
    )

    apr_port = FakeSimulateAprV2Port(initialized_ticks=[])
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            return_empty_fetch=True,
            initialized_ticks_rows=[],
        ),
    )

    with pytest.raises(SimulationDataNotFoundError) as exc:
        use_case.execute(
            replace(
                base_input,
                tick_lower=None,
                tick_upper=None,
                min_price=Decimal("1"),
                max_price=Decimal("2"),
                calculation_method="custom",
                custom_calculation_price=Decimal("2"),
            )
        )

    assert exc.value.code == "price_range_boundaries_not_snapshotable"
    assert exc.value.context["raw_tick_lower"] == -11
    assert exc.value.context["raw_tick_upper"] == 11
    assert exc.value.context["snapped_tick_lower"] == -20
    assert exc.value.context["snapped_tick_upper"] == 20
    assert exc.value.context["adjusted_tick_lower"] is None
    assert exc.value.context["adjusted_tick_upper"] is None
    assert "missing" in exc.value.context


def test_resolve_range_ticks_full_range_uses_uniswap_math_bounds(base_input: SimulateAprV2Input):
    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )
    pool = apr_port.get_pool(pool_address="0xpool", chain_id=1, dex_id=2)
    assert pool is not None

    tick_lower, tick_upper = use_case._resolve_range_ticks(
        command=replace(
            base_input,
            full_range=True,
            tick_lower=None,
            tick_upper=None,
            min_price=None,
            max_price=None,
        ),
        pool=pool,
    )

    assert (tick_lower, tick_upper) == (UNISWAP_V3_MIN_TICK, UNISWAP_V3_MAX_TICK)
    assert tick_lower != -887280
    assert tick_upper != 887280


def test_execute_full_range_exact_fallbacks_to_initialized_tick_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )
    apr_port = FakeSimulateAprV2Port()
    on_demand_port = FakeTickSnapshotOnDemandPort(
        apr_port=apr_port,
        return_empty_fetch=True,
    )
    use_case = _make_use_case(apr_port=apr_port, on_demand_port=on_demand_port)

    boundary_attempts: list[tuple[int, int]] = []
    original_ensure = use_case._ensure_tick_snapshots_present

    def _capture_ensure(**kwargs):
        tick_indices = kwargs["tick_indices"]
        boundary_attempts.append((int(tick_indices[0]), int(tick_indices[1])))
        return original_ensure(**kwargs)

    monkeypatch.setattr(use_case, "_ensure_tick_snapshots_present", _capture_ensure)

    result = use_case.execute(
        replace(
            base_input,
            full_range=True,
            tick_lower=None,
            tick_upper=None,
            min_price=None,
            max_price=None,
            calculation_method="custom",
            custom_calculation_price=Decimal("2"),
        )
    )

    assert result.estimated_fees_period_usd > Decimal("0")
    assert boundary_attempts[0] == (UNISWAP_V3_MIN_TICK, UNISWAP_V3_MAX_TICK)
    assert boundary_attempts[1] == (-10, 10)
    assert -887280 not in {tick for pair in boundary_attempts for tick in pair}
    assert 887280 not in {tick for pair in boundary_attempts for tick in pair}


@pytest.mark.parametrize(
    "calculation_method",
    ["avg_liquidity_in_range", "peak_liquidity_in_range"],
)
def test_execute_full_range_with_liquidity_in_range_method_falls_back_to_current(
    monkeypatch: pytest.MonkeyPatch,
    base_input: SimulateAprV2Input,
    calculation_method: str,
):
    monkeypatch.setattr(
        "app.application.use_cases.simulate_apr_v2.position_liquidity_v3",
        lambda **_: Decimal("10"),
    )
    apr_port = FakeSimulateAprV2Port()
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(apr_port=apr_port),
    )

    captured_method: dict[str, str] = {}
    original_resolve_calculation_price = use_case._resolve_calculation_price

    def _capture_resolve_calculation_price(*, command, **kwargs):
        captured_method["value"] = command.calculation_method
        return original_resolve_calculation_price(command=command, **kwargs)

    monkeypatch.setattr(use_case, "_resolve_calculation_price", _capture_resolve_calculation_price)

    result = use_case.execute(
        replace(
            base_input,
            full_range=True,
            calculation_method=calculation_method,
            custom_calculation_price=None,
        )
    )

    assert result.estimated_fees_period_usd > Decimal("0")
    assert captured_method["value"] == "current"


def test_execute_full_range_exact_raises_specific_error_when_boundaries_not_snapshotable(
    base_input: SimulateAprV2Input,
):
    apr_port = FakeSimulateAprV2Port(initialized_ticks=[])
    use_case = _make_use_case(
        apr_port=apr_port,
        on_demand_port=FakeTickSnapshotOnDemandPort(
            apr_port=apr_port,
            return_empty_fetch=True,
            initialized_ticks_rows=[],
        ),
    )

    with pytest.raises(SimulationDataNotFoundError) as exc:
        use_case.execute(
            replace(
                base_input,
                full_range=True,
                tick_lower=None,
                tick_upper=None,
                min_price=None,
                max_price=None,
                calculation_method="custom",
                custom_calculation_price=Decimal("2"),
            )
        )

    assert exc.value.code == "full_range_boundaries_not_snapshotable"
    assert exc.value.context["range_mode"] == "full_range"
    assert exc.value.context["pool_address"] == "0xpool"
    assert exc.value.context["chain_id"] == 1
    assert exc.value.context["dex_id"] == 2
    assert exc.value.context["raw_tick_lower"] == UNISWAP_V3_MIN_TICK
    assert exc.value.context["raw_tick_upper"] == UNISWAP_V3_MAX_TICK
    assert exc.value.context["snapped_tick_lower"] == UNISWAP_V3_MIN_TICK
    assert exc.value.context["snapped_tick_upper"] == UNISWAP_V3_MAX_TICK
    assert exc.value.context["adjusted_tick_lower"] is None
    assert exc.value.context["adjusted_tick_upper"] is None
    assert "missing" in exc.value.context
