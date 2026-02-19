from __future__ import annotations

import logging
import re
from decimal import Decimal
from time import perf_counter
from typing import NoReturn

from app.application.dto.simulate_apr_v2 import (
    SimulateAprV2Input,
    SimulateAprV2MetaOutput,
    SimulateAprV2Output,
)
from app.application.dto.tick_snapshot_on_demand import MissingTickSnapshot
from app.application.ports.simulate_apr_v2_port import SimulateAprV2Port
from app.application.ports.tick_snapshot_on_demand_port import TickSnapshotOnDemandPort
from app.domain.entities.simulate_apr import SimulateAprInitializedTick
from app.domain.entities.simulate_apr_v2 import (
    SimulateAprV2Pool,
    SimulateAprV2PoolSnapshot,
    SimulateAprV2TickSnapshot,
)
from app.domain.exceptions import (
    InvalidSimulationInputError,
    PoolNotFoundError,
    SimulationDataNotFoundError,
)
from app.domain.services.liquidity import (
    LiquidityCurve,
    active_liquidity_at_tick,
    build_liquidity_curve,
    position_liquidity_v3,
)
from app.domain.services.univ3_fee_growth import (
    fee_growth_inside,
    fees_from_delta_inside,
    parse_uint256,
)
from app.domain.services.univ3_math import (
    price_to_tick_ceil,
    price_to_tick_floor,
    sqrt_price_x96_to_price,
    sqrt_price_x96_to_sqrt_price,
    tick_to_price,
    tick_to_sqrt_price,
)


HORIZON_PATTERN = re.compile(r"^\s*(\d+)\s*([dDhH]?)\s*$")
CALCULATION_METHODS = {"current", "avg_liquidity_in_range", "peak_liquidity_in_range", "custom"}
UNISWAP_V3_MIN_TICK = -887272
UNISWAP_V3_MAX_TICK = 887272
DATA_NOT_FOUND_MESSAGE = "Nao foi possivel realizar a simulacao com os dados disponiveis."
SECONDS_PER_DAY = 86400
logger = logging.getLogger(__name__)


class SimulateAprV2UseCase:
    def __init__(
        self,
        *,
        simulate_apr_v2_port: SimulateAprV2Port,
        tick_snapshot_on_demand_port: TickSnapshotOnDemandPort,
        max_on_demand_combinations: int = 4,
    ):
        self._simulate_apr_v2_port = simulate_apr_v2_port
        self._tick_snapshot_on_demand_port = tick_snapshot_on_demand_port
        self._max_on_demand_combinations = max(1, max_on_demand_combinations)

    def execute(self, command: SimulateAprV2Input) -> SimulateAprV2Output:
        logger.info(
            "simulate_apr_v2: start pool=%s chain_id=%s dex_id=%s lookback_days=%s full_range=%s method=%s apr_method=%s",
            command.pool_address,
            command.chain_id,
            command.dex_id,
            command.lookback_days,
            command.full_range,
            command.calculation_method,
            command.apr_method,
        )
        if not command.pool_address or not command.pool_address.lower().startswith("0x"):
            raise InvalidSimulationInputError("pool_address must start with 0x.")
        if command.chain_id <= 0 or command.dex_id <= 0:
            raise InvalidSimulationInputError("chain_id and dex_id must be positive integers.")
        if command.lookback_days <= 0:
            raise InvalidSimulationInputError("lookback_days must be > 0.")

        self._parse_horizon(command.horizon)

        apr_method = command.apr_method.strip().lower()
        if apr_method != "exact":
            raise InvalidSimulationInputError("apr_method must be exact.")

        calculation_method = command.calculation_method.strip().lower()
        if calculation_method not in CALCULATION_METHODS:
            raise InvalidSimulationInputError(
                "calculation_method must be one of: current, avg_liquidity_in_range, peak_liquidity_in_range, custom."
            )
        if calculation_method == "custom":
            if command.custom_calculation_price is None or command.custom_calculation_price <= 0:
                raise InvalidSimulationInputError(
                    "custom_calculation_price must be provided and > 0 when calculation_method=custom."
                )

        if command.deposit_usd is None and command.amount_token0 is None and command.amount_token1 is None:
            raise InvalidSimulationInputError(
                "Provide deposit_usd or at least one token amount (amount_token0/amount_token1)."
            )
        if command.deposit_usd is not None and command.deposit_usd <= 0:
            raise InvalidSimulationInputError("deposit_usd must be positive.")

        amount_token0 = command.amount_token0 if command.amount_token0 is not None else Decimal("0")
        amount_token1 = command.amount_token1 if command.amount_token1 is not None else Decimal("0")
        if amount_token0 < 0 or amount_token1 < 0:
            raise InvalidSimulationInputError("amount_token0 and amount_token1 must be >= 0.")

        pool_address = command.pool_address.lower()
        pool = self._simulate_apr_v2_port.get_pool(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
        if pool is None:
            raise PoolNotFoundError("Pool not found.")

        tick_lower, tick_upper = self._resolve_range_ticks(command=command, pool=pool)

        snapshot_b = self._simulate_apr_v2_port.get_latest_pool_snapshot(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
        if snapshot_b is None:
            self._raise_data_not_found(
                "latest_pool_snapshot_not_found",
                pool_address=pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
            )

        target_ts = snapshot_b.block_timestamp - (command.lookback_days * SECONDS_PER_DAY)
        snapshot_a = self._simulate_apr_v2_port.get_lookback_pool_snapshot(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
            target_timestamp=target_ts,
        )
        if snapshot_a is None:
            self._raise_data_not_found(
                "lookback_pool_snapshot_not_found",
                pool_address=pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                target_timestamp=target_ts,
                block_b=snapshot_b.block_number,
                ts_b=snapshot_b.block_timestamp,
            )

        if snapshot_a.tick is None or snapshot_b.tick is None:
            self._raise_data_not_found(
                "snapshot_tick_missing",
                block_a=snapshot_a.block_number,
                block_b=snapshot_b.block_number,
                tick_a=snapshot_a.tick,
                tick_b=snapshot_b.tick,
            )

        seconds_delta = snapshot_b.block_timestamp - snapshot_a.block_timestamp
        if seconds_delta <= 0:
            self._raise_data_not_found(
                "invalid_seconds_delta",
                block_a=snapshot_a.block_number,
                ts_a=snapshot_a.block_timestamp,
                block_b=snapshot_b.block_number,
                ts_b=snapshot_b.block_timestamp,
                seconds_delta=seconds_delta,
            )

        warnings: list[str] = []
        calculation_price = self._resolve_calculation_price(
            command=command,
            pool=pool,
            snapshot_b=snapshot_b,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
        )
        if calculation_price <= 0:
            raise InvalidSimulationInputError("calculation_price must be positive.")

        if (
            command.deposit_usd is not None
            and command.deposit_usd > 0
            and amount_token0 == 0
            and amount_token1 == 0
        ):
            usd_half = command.deposit_usd / Decimal("2")
            amount_token0 = usd_half / calculation_price
            amount_token1 = usd_half
            warnings.append("Derived token amounts from deposit_usd using calculation price (50/50 split).")

        self._ensure_tick_snapshots_present(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
            block_numbers=[snapshot_a.block_number, snapshot_b.block_number],
            tick_indices=[tick_lower, tick_upper],
        )

        tick_snapshots = self._simulate_apr_v2_port.get_tick_snapshots_for_blocks(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
            block_numbers=[snapshot_a.block_number, snapshot_b.block_number],
            tick_indices=[tick_lower, tick_upper],
        )
        tick_map = {
            (row.block_number, row.tick_idx): row
            for row in tick_snapshots
        }

        tick_a_lower = self._require_tick_snapshot(tick_map, snapshot_a.block_number, tick_lower)
        tick_a_upper = self._require_tick_snapshot(tick_map, snapshot_a.block_number, tick_upper)
        tick_b_lower = self._require_tick_snapshot(tick_map, snapshot_b.block_number, tick_lower)
        tick_b_upper = self._require_tick_snapshot(tick_map, snapshot_b.block_number, tick_upper)

        delta_inside0, delta_inside1 = self._calculate_delta_inside(
            snapshot_a=snapshot_a,
            snapshot_b=snapshot_b,
            tick_a_lower=tick_a_lower,
            tick_a_upper=tick_a_upper,
            tick_b_lower=tick_b_lower,
            tick_b_upper=tick_b_upper,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
        )

        sqrt_price_current = self._resolve_sqrt_price_current(snapshot_b)
        sqrt_price_lower = tick_to_sqrt_price(tick_lower)
        sqrt_price_upper = tick_to_sqrt_price(tick_upper)
        l_user = position_liquidity_v3(
            amount_token0=amount_token0,
            amount_token1=amount_token1,
            sqrt_price_current=sqrt_price_current,
            sqrt_price_lower=sqrt_price_lower,
            sqrt_price_upper=sqrt_price_upper,
            token0_decimals=pool.token0_decimals,
            token1_decimals=pool.token1_decimals,
        )
        if l_user <= 0:
            warnings.append("User liquidity is zero for the informed amounts/range.")

        fees_token0_raw = fees_from_delta_inside(delta_inside=delta_inside0, user_liquidity=l_user)
        fees_token1_raw = fees_from_delta_inside(delta_inside=delta_inside1, user_liquidity=l_user)
        fees_token0 = fees_token0_raw / (Decimal(10) ** Decimal(pool.token0_decimals))
        fees_token1 = fees_token1_raw / (Decimal(10) ** Decimal(pool.token1_decimals))
        fees_period_usd = fees_token1 + (fees_token0 * calculation_price)

        estimated_fees_24h_usd = fees_period_usd * (Decimal(SECONDS_PER_DAY) / Decimal(seconds_delta))
        yearly_usd = fees_period_usd * (Decimal(365 * SECONDS_PER_DAY) / Decimal(seconds_delta))
        monthly_usd = yearly_usd / Decimal("12")

        deposit_usd = command.deposit_usd
        if deposit_usd is None:
            deposit_usd = amount_token1 + (amount_token0 * calculation_price)
            warnings.append("deposit_usd derived from amount_token0/amount_token1 using calculation price.")

        fee_apr = Decimal("0")
        if deposit_usd > 0:
            fee_apr = yearly_usd / deposit_usd

        logger.info(
            "simulate_apr_v2: success pool=%s chain_id=%s dex_id=%s block_a=%s block_b=%s seconds_delta=%s fees_period_usd=%s fee_apr=%s",
            pool_address,
            command.chain_id,
            command.dex_id,
            snapshot_a.block_number,
            snapshot_b.block_number,
            seconds_delta,
            fees_period_usd,
            fee_apr,
        )

        return SimulateAprV2Output(
            estimated_fees_period_usd=fees_period_usd,
            estimated_fees_24h_usd=estimated_fees_24h_usd,
            monthly_usd=monthly_usd,
            yearly_usd=yearly_usd,
            fee_apr=fee_apr,
            meta=SimulateAprV2MetaOutput(
                block_a_number=snapshot_a.block_number,
                block_b_number=snapshot_b.block_number,
                ts_a=snapshot_a.block_timestamp,
                ts_b=snapshot_b.block_timestamp,
                seconds_delta=seconds_delta,
                used_price=calculation_price,
                warnings=warnings,
            ),
        )

    def _ensure_tick_snapshots_present(
        self,
        *,
        pool_address: str,
        chain_id: int,
        dex_id: int,
        block_numbers: list[int],
        tick_indices: list[int],
    ) -> None:
        missing = self._tick_snapshot_on_demand_port.get_missing_tick_snapshots(
            pool_address=pool_address,
            chain_id=chain_id,
            dex_id=dex_id,
            block_numbers=block_numbers,
            tick_indices=tick_indices,
        )
        if not missing:
            logger.info(
                "simulate_apr_v2: on_demand_check no_missing_ticks pool=%s chain_id=%s dex_id=%s",
                pool_address,
                chain_id,
                dex_id,
            )
            return

        if len(missing) > self._max_on_demand_combinations:
            self._raise_data_not_found(
                "on_demand_too_many_combinations",
                pool_address=pool_address,
                chain_id=chain_id,
                dex_id=dex_id,
                missing=self._format_missing(missing),
                max_allowed=self._max_on_demand_combinations,
            )

        logger.info(
            "simulate_apr_v2: on_demand_fetch_start pool=%s chain_id=%s dex_id=%s missing=%s",
            pool_address,
            chain_id,
            dex_id,
            self._format_missing(missing),
        )
        start = perf_counter()
        try:
            fetched = self._tick_snapshot_on_demand_port.fetch_tick_snapshots(
                pool_address=pool_address,
                chain_id=chain_id,
                dex_id=dex_id,
                combinations=missing,
            )
        except RuntimeError as exc:
            logger.warning(
                "simulate_apr_v2: on_demand_fetch_failed pool=%s chain_id=%s dex_id=%s error=%s",
                pool_address,
                chain_id,
                dex_id,
                exc,
            )
            raise SimulationDataNotFoundError(
                f"{DATA_NOT_FOUND_MESSAGE} Falha no on-demand do subgraph: {exc}"
            ) from exc

        fetched_by_combo = {(row.block_number, row.tick_idx): row for row in fetched}
        rows_to_upsert = [
            fetched_by_combo[(combo.block_number, combo.tick_idx)]
            for combo in missing
            if (combo.block_number, combo.tick_idx) in fetched_by_combo
        ]
        if rows_to_upsert:
            self._tick_snapshot_on_demand_port.upsert_tick_snapshots(rows=rows_to_upsert)

        try:
            block_rows = self._tick_snapshot_on_demand_port.fetch_blocks_metadata(
                chain_id=chain_id,
                block_numbers=block_numbers,
            )
            if block_rows:
                self._tick_snapshot_on_demand_port.upsert_blocks(rows=block_rows)
        except RuntimeError as exc:
            logger.warning(
                "simulate_apr_v2: on_demand_blocks_upsert_failed chain_id=%s blocks=%s error=%s",
                chain_id,
                sorted(set(block_numbers)),
                exc,
            )

        remaining = self._tick_snapshot_on_demand_port.get_missing_tick_snapshots(
            pool_address=pool_address,
            chain_id=chain_id,
            dex_id=dex_id,
            block_numbers=block_numbers,
            tick_indices=tick_indices,
        )
        elapsed_ms = (perf_counter() - start) * 1000
        logger.info(
            "simulate_apr_v2: on_demand_fetch_end pool=%s chain_id=%s dex_id=%s requested=%s fetched=%s remaining=%s elapsed_ms=%.2f",
            pool_address,
            chain_id,
            dex_id,
            len(missing),
            len(rows_to_upsert),
            len(remaining),
            elapsed_ms,
        )

        if remaining:
            raise SimulationDataNotFoundError(
                f"{DATA_NOT_FOUND_MESSAGE} Missing tick snapshots: {self._format_missing(remaining)}"
            )

    def _resolve_range_ticks(self, *, command: SimulateAprV2Input, pool: SimulateAprV2Pool) -> tuple[int, int]:
        if command.full_range:
            tick_spacing = pool.tick_spacing
            if tick_spacing is None or tick_spacing <= 0:
                raise InvalidSimulationInputError("tick_spacing must be available and > 0 for full_range simulation.")

            tick_lower = (UNISWAP_V3_MIN_TICK // tick_spacing) * tick_spacing
            tick_upper = ((UNISWAP_V3_MAX_TICK + tick_spacing - 1) // tick_spacing) * tick_spacing
            if tick_lower >= tick_upper:
                raise InvalidSimulationInputError("Invalid full range ticks computed for this pool.")
            return tick_lower, tick_upper

        if command.tick_lower is not None or command.tick_upper is not None:
            if command.tick_lower is None or command.tick_upper is None:
                raise InvalidSimulationInputError("tick_lower and tick_upper must be provided together.")
            if command.tick_lower >= command.tick_upper:
                raise InvalidSimulationInputError("tick_lower must be lower than tick_upper.")
            return command.tick_lower, command.tick_upper

        if command.min_price is None or command.max_price is None:
            raise InvalidSimulationInputError(
                "Provide either tick range (tick_lower/tick_upper) or price range (min_price/max_price)."
            )
        if command.min_price <= 0 or command.max_price <= 0:
            raise InvalidSimulationInputError("min_price and max_price must be positive.")
        if command.min_price >= command.max_price:
            raise InvalidSimulationInputError("min_price must be lower than max_price.")

        try:
            tick_lower = price_to_tick_floor(
                command.min_price,
                pool.token0_decimals,
                pool.token1_decimals,
            )
            tick_upper = price_to_tick_ceil(
                command.max_price,
                pool.token0_decimals,
                pool.token1_decimals,
            )
        except ValueError as exc:
            raise InvalidSimulationInputError(str(exc)) from exc
        if tick_lower >= tick_upper:
            raise InvalidSimulationInputError("Invalid price range for tick conversion.")
        return tick_lower, tick_upper

    def _resolve_calculation_price(
        self,
        *,
        command: SimulateAprV2Input,
        pool: SimulateAprV2Pool,
        snapshot_b: SimulateAprV2PoolSnapshot,
        tick_lower: int,
        tick_upper: int,
    ) -> Decimal:
        method = command.calculation_method.strip().lower()
        current_price = self._resolve_current_price(snapshot=snapshot_b, pool=pool)

        if method == "current":
            return current_price

        if method == "custom":
            custom_price = command.custom_calculation_price
            if custom_price is None or custom_price <= 0:
                raise InvalidSimulationInputError(
                    "custom_calculation_price must be provided and > 0 when calculation_method=custom."
                )
            return custom_price

        if command.full_range:
            raise InvalidSimulationInputError(
                "calculation_method avg_liquidity_in_range and peak_liquidity_in_range are not supported with full_range=true."
            )

        initialized_ticks = self._simulate_apr_v2_port.get_initialized_ticks(
            pool_address=command.pool_address.lower(),
            chain_id=command.chain_id,
            dex_id=command.dex_id,
            min_tick=tick_lower,
            max_tick=tick_upper,
        )
        if not initialized_ticks:
            self._raise_data_not_found(
                "initialized_ticks_not_found",
                pool_address=command.pool_address.lower(),
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
            )

        liquidity_curve = build_liquidity_curve(initialized_ticks)
        candidates = self._build_tick_candidates(
            initialized_ticks=initialized_ticks,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
        )
        if not candidates:
            self._raise_data_not_found(
                "no_tick_candidates_in_range",
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                initialized_ticks=len(initialized_ticks),
            )

        if method == "peak_liquidity_in_range":
            peak_tick = self._find_peak_tick(
                candidates=candidates,
                liquidity_curve=liquidity_curve,
                current_tick=snapshot_b.tick,
            )
            return tick_to_price(peak_tick, pool.token0_decimals, pool.token1_decimals)

        if method == "avg_liquidity_in_range":
            avg_tick = self._find_weighted_avg_tick(
                candidates=candidates,
                liquidity_curve=liquidity_curve,
            )
            if avg_tick is None:
                self._raise_data_not_found(
                    "weighted_avg_tick_not_found",
                    tick_lower=tick_lower,
                    tick_upper=tick_upper,
                    candidates=len(candidates),
                )
            return tick_to_price(avg_tick, pool.token0_decimals, pool.token1_decimals)

        logger.warning("simulate_apr_v2: unsupported calculation_method=%s", method)
        raise InvalidSimulationInputError("Unsupported calculation_method.")

    def _build_tick_candidates(
        self,
        *,
        initialized_ticks: list[SimulateAprInitializedTick],
        tick_lower: int,
        tick_upper: int,
    ) -> list[int]:
        unique_ticks = {
            row.tick_idx
            for row in initialized_ticks
            if tick_lower <= row.tick_idx <= tick_upper
        }
        return sorted(unique_ticks)

    def _find_peak_tick(
        self,
        *,
        candidates: list[int],
        liquidity_curve: LiquidityCurve,
        current_tick: int | None,
    ) -> int:
        if current_tick is None:
            self._raise_data_not_found("peak_tick_current_tick_missing")

        best_tick: int | None = None
        best_liquidity = Decimal("-1")
        best_distance: int | None = None
        for tick in candidates:
            liquidity = active_liquidity_at_tick(curve=liquidity_curve, tick=tick)
            distance = abs(tick - current_tick)
            if (
                best_tick is None
                or liquidity > best_liquidity
                or (
                    liquidity == best_liquidity
                    and best_distance is not None
                    and (distance < best_distance or (distance == best_distance and tick < best_tick))
                )
            ):
                best_tick = tick
                best_liquidity = liquidity
                best_distance = distance

        if best_tick is None:
            self._raise_data_not_found("peak_tick_not_found", candidates=len(candidates))
        return best_tick

    def _find_weighted_avg_tick(
        self,
        *,
        candidates: list[int],
        liquidity_curve: LiquidityCurve,
    ) -> int | None:
        sum_w = Decimal("0")
        sum_wt = Decimal("0")
        for tick in candidates:
            liquidity = active_liquidity_at_tick(curve=liquidity_curve, tick=tick)
            if liquidity <= 0:
                continue
            sum_w += liquidity
            sum_wt += liquidity * Decimal(tick)

        if sum_w <= 0:
            return None
        return int((sum_wt / sum_w).to_integral_value())

    def _resolve_current_price(self, *, snapshot: SimulateAprV2PoolSnapshot, pool: SimulateAprV2Pool) -> Decimal:
        if snapshot.sqrt_price_x96 is not None and snapshot.sqrt_price_x96 > 0:
            return sqrt_price_x96_to_price(
                snapshot.sqrt_price_x96,
                pool.token0_decimals,
                pool.token1_decimals,
            )

        if snapshot.tick is None:
            self._raise_data_not_found(
                "current_price_tick_missing",
                block_number=snapshot.block_number,
                sqrt_price_x96=snapshot.sqrt_price_x96,
            )
        return tick_to_price(snapshot.tick, pool.token0_decimals, pool.token1_decimals)

    def _resolve_sqrt_price_current(self, snapshot_b: SimulateAprV2PoolSnapshot) -> Decimal:
        if snapshot_b.sqrt_price_x96 is not None and snapshot_b.sqrt_price_x96 > 0:
            return sqrt_price_x96_to_sqrt_price(snapshot_b.sqrt_price_x96)
        if snapshot_b.tick is None:
            self._raise_data_not_found(
                "sqrt_price_current_missing_tick",
                block_number=snapshot_b.block_number,
            )
        return tick_to_sqrt_price(snapshot_b.tick)

    def _require_tick_snapshot(
        self,
        tick_map: dict[tuple[int, int], SimulateAprV2TickSnapshot],
        block_number: int,
        tick_idx: int,
    ) -> SimulateAprV2TickSnapshot:
        row = tick_map.get((block_number, tick_idx))
        if row is None:
            self._raise_data_not_found(
                "tick_snapshot_missing",
                block_number=block_number,
                tick_idx=tick_idx,
                available_keys=len(tick_map),
            )
        return row

    def _calculate_delta_inside(
        self,
        *,
        snapshot_a: SimulateAprV2PoolSnapshot,
        snapshot_b: SimulateAprV2PoolSnapshot,
        tick_a_lower: SimulateAprV2TickSnapshot,
        tick_a_upper: SimulateAprV2TickSnapshot,
        tick_b_lower: SimulateAprV2TickSnapshot,
        tick_b_upper: SimulateAprV2TickSnapshot,
        tick_lower: int,
        tick_upper: int,
    ) -> tuple[int, int]:
        try:
            global0_a = parse_uint256(snapshot_a.fee_growth_global0_x128)
            global1_a = parse_uint256(snapshot_a.fee_growth_global1_x128)
            global0_b = parse_uint256(snapshot_b.fee_growth_global0_x128)
            global1_b = parse_uint256(snapshot_b.fee_growth_global1_x128)

            outside0_a_lower = parse_uint256(tick_a_lower.fee_growth_outside0_x128)
            outside0_a_upper = parse_uint256(tick_a_upper.fee_growth_outside0_x128)
            outside1_a_lower = parse_uint256(tick_a_lower.fee_growth_outside1_x128)
            outside1_a_upper = parse_uint256(tick_a_upper.fee_growth_outside1_x128)

            outside0_b_lower = parse_uint256(tick_b_lower.fee_growth_outside0_x128)
            outside0_b_upper = parse_uint256(tick_b_upper.fee_growth_outside0_x128)
            outside1_b_lower = parse_uint256(tick_b_lower.fee_growth_outside1_x128)
            outside1_b_upper = parse_uint256(tick_b_upper.fee_growth_outside1_x128)

            if snapshot_a.tick is None or snapshot_b.tick is None:
                raise ValueError("Missing pool tick.")

            inside0_a = fee_growth_inside(
                fee_growth_global=global0_a,
                fee_growth_outside_lower=outside0_a_lower,
                fee_growth_outside_upper=outside0_a_upper,
                tick_current=snapshot_a.tick,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
            )
            inside1_a = fee_growth_inside(
                fee_growth_global=global1_a,
                fee_growth_outside_lower=outside1_a_lower,
                fee_growth_outside_upper=outside1_a_upper,
                tick_current=snapshot_a.tick,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
            )
            inside0_b = fee_growth_inside(
                fee_growth_global=global0_b,
                fee_growth_outside_lower=outside0_b_lower,
                fee_growth_outside_upper=outside0_b_upper,
                tick_current=snapshot_b.tick,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
            )
            inside1_b = fee_growth_inside(
                fee_growth_global=global1_b,
                fee_growth_outside_lower=outside1_b_lower,
                fee_growth_outside_upper=outside1_b_upper,
                tick_current=snapshot_b.tick,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
            )

            delta_inside0 = inside0_b - inside0_a
            delta_inside1 = inside1_b - inside1_a
            if delta_inside0 < 0 or delta_inside1 < 0:
                raise ValueError("Negative deltaInside.")
            return delta_inside0, delta_inside1
        except (TypeError, ValueError) as exc:
            logger.warning(
                "simulate_apr_v2: invalid exact fee growth data block_a=%s block_b=%s tick_lower=%s tick_upper=%s error=%s",
                snapshot_a.block_number,
                snapshot_b.block_number,
                tick_lower,
                tick_upper,
                exc,
            )
            raise SimulationDataNotFoundError(DATA_NOT_FOUND_MESSAGE) from exc

    def _parse_horizon(self, horizon_raw: str) -> tuple[int, Decimal]:
        raw = horizon_raw.strip().lower()
        match = HORIZON_PATTERN.match(raw)
        if not match:
            raise InvalidSimulationInputError("horizon must be a positive value like 24h, 7d or 14d.")

        value = int(match.group(1))
        unit = match.group(2).lower() or "d"
        if value <= 0:
            raise InvalidSimulationInputError("horizon must be positive.")

        if unit == "h":
            horizon_hours = value
            annualization_days = Decimal(value) / Decimal("24")
        else:
            horizon_hours = value * 24
            annualization_days = Decimal(value)

        if horizon_hours <= 0 or annualization_days <= 0:
            raise InvalidSimulationInputError("horizon must be positive.")
        return horizon_hours, annualization_days

    def _raise_data_not_found(self, reason: str, **context) -> NoReturn:
        logger.warning("simulate_apr_v2: data_not_found reason=%s context=%s", reason, context)
        raise SimulationDataNotFoundError(DATA_NOT_FOUND_MESSAGE)

    def _format_missing(self, missing: list[MissingTickSnapshot]) -> list[tuple[int, int]]:
        return [(item.block_number, item.tick_idx) for item in missing]
