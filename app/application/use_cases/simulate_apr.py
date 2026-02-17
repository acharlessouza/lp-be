from __future__ import annotations

import logging
import re
from decimal import Decimal

from app.application.dto.simulate_apr import (
    SimulateAprInput,
    SimulateAprOutput,
)
from app.application.ports.simulate_apr_port import SimulateAprPort
from app.domain.entities.simulate_apr import SimulateAprInitializedTick, SimulateAprPool, SimulateAprPoolState
from app.domain.exceptions import InvalidSimulationInputError, PoolNotFoundError, SimulationDataNotFoundError
from app.domain.services.apr_simulation import simulate_fee_apr
from app.domain.services.liquidity import (
    LiquidityCurve,
    active_liquidity_at_tick,
    build_liquidity_curve,
    position_liquidity_v3,
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
logger = logging.getLogger(__name__)


class SimulateAprUseCase:
    def __init__(self, *, simulate_apr_port: SimulateAprPort):
        self._simulate_apr_port = simulate_apr_port

    def execute(self, command: SimulateAprInput) -> SimulateAprOutput:
        if not command.pool_address or not command.pool_address.lower().startswith("0x"):
            raise InvalidSimulationInputError("pool_address must start with 0x.")
        if command.chain_id <= 0 or command.dex_id <= 0:
            raise InvalidSimulationInputError("chain_id and dex_id must be positive integers.")

        horizon_hours, annualization_days = self._parse_horizon(command.horizon)
        if command.lookback_days <= 0:
            raise InvalidSimulationInputError("lookback_days must be > 0.")

        mode = command.mode.strip().upper()
        if mode not in {"A", "B"}:
            raise InvalidSimulationInputError("mode must be A or B.")

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
        pool = self._simulate_apr_port.get_pool(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
        if pool is None:
            raise PoolNotFoundError("Pool not found.")

        latest_state = self._simulate_apr_port.get_latest_pool_state(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
        if latest_state is None:
            raise SimulationDataNotFoundError("Pool state not found.")

        current_tick = latest_state.tick
        if current_tick is None:
            raise SimulationDataNotFoundError("Pool current tick not found.")

        tick_lower, tick_upper = self._resolve_range_ticks(command=command, pool=pool)

        hours_to_fetch = command.lookback_days * 24
        hourly_fees = self._simulate_apr_port.get_pool_hourly(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
            hours=hours_to_fetch,
        )
        if not hourly_fees:
            raise SimulationDataNotFoundError("Pool hourly data not found.")

        warnings: list[str] = []
        snapshots_map: dict = {}
        if mode == "B":
            snapshots = self._simulate_apr_port.get_pool_state_snapshots_hourly(
                pool_address=pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                hours=hours_to_fetch,
            )
            snapshots_map = {
                row.hour_ts: row.tick
                for row in snapshots
                if row.tick is not None
            }
            if not snapshots_map:
                warnings.append("No hourly snapshots found; mode B fell back to mode A behavior.")

        initialized_ticks = self._simulate_apr_port.get_initialized_ticks(
            pool_address=pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
            min_tick=tick_lower,
            max_tick=tick_upper,
        )
        if not initialized_ticks:
            raise SimulationDataNotFoundError("Initialized ticks not found for pool.")

        liquidity_curve = build_liquidity_curve(initialized_ticks)
        calculation_price = self._resolve_calculation_price(
            method=calculation_method,
            custom_price=command.custom_calculation_price,
            current_tick=current_tick,
            latest_state=latest_state,
            pool=pool,
            liquidity_curve=liquidity_curve,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            initialized_ticks=initialized_ticks,
            warnings=warnings,
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

        sqrt_price_current = None
        if latest_state.sqrt_price_x96 is not None and latest_state.sqrt_price_x96 > 0:
            sqrt_price_current = sqrt_price_x96_to_sqrt_price(latest_state.sqrt_price_x96)
        else:
            sqrt_price_current = tick_to_sqrt_price(current_tick)

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

        deposit_usd = command.deposit_usd
        if deposit_usd is None:
            if calculation_price > 0:
                deposit_usd = amount_token1 + (amount_token0 * calculation_price)
                warnings.append(
                    "deposit_usd derived from amount_token0/amount_token1 using calculation price."
                )
            else:
                warnings.append("Could not derive deposit_usd from amounts and calculation price.")

        simulation = simulate_fee_apr(
            hourly_fees=hourly_fees,
            hourly_ticks=snapshots_map,
            liquidity_curve=liquidity_curve,
            l_user=l_user,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            mode=mode,
            fallback_tick=current_tick,
            horizon_hours=horizon_hours,
            annualization_days=annualization_days,
            deposit_usd=deposit_usd,
            warnings=warnings,
        )

        return SimulateAprOutput(
            estimated_fees_24h_usd=simulation.estimated_fees_24h_usd,
            monthly_usd=simulation.monthly_usd,
            yearly_usd=simulation.yearly_usd,
            fee_apr=simulation.fee_apr,
        )

    def _resolve_range_ticks(self, *, command: SimulateAprInput, pool: SimulateAprPool) -> tuple[int, int]:
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

    def _resolve_current_price(
        self,
        *,
        current_tick: int,
        latest_state: SimulateAprPoolState,
        token0_decimals: int,
        token1_decimals: int,
    ) -> Decimal:
        if latest_state.sqrt_price_x96 is not None and latest_state.sqrt_price_x96 > 0:
            return sqrt_price_x96_to_price(
                latest_state.sqrt_price_x96,
                token0_decimals,
                token1_decimals,
            )
        return tick_to_price(current_tick, token0_decimals, token1_decimals)

    def _resolve_calculation_price(
        self,
        *,
        method: str,
        custom_price: Decimal | None,
        current_tick: int,
        latest_state: SimulateAprPoolState,
        pool: SimulateAprPool,
        liquidity_curve: LiquidityCurve,
        tick_lower: int,
        tick_upper: int,
        initialized_ticks: list[SimulateAprInitializedTick],
        warnings: list[str] | None = None,
    ) -> Decimal:
        current_price = self._resolve_current_price(
            current_tick=current_tick,
            latest_state=latest_state,
            token0_decimals=pool.token0_decimals,
            token1_decimals=pool.token1_decimals,
        )

        if method == "current":
            return current_price

        if method == "custom":
            if custom_price is None or custom_price <= 0:
                raise InvalidSimulationInputError(
                    "custom_calculation_price must be provided and > 0 when calculation_method=custom."
                )
            return custom_price

        candidates = self._build_tick_candidates(
            initialized_ticks=initialized_ticks,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
        )
        if not candidates:
            if warnings is not None:
                warnings.append(
                    f"No initialized tick candidate in range for method={method}; using current price."
                )
            logger.warning(
                "simulate_apr: no candidates for method=%s in range [%s, %s], using current price",
                method,
                tick_lower,
                tick_upper,
            )
            return current_price

        if method == "peak_liquidity_in_range":
            peak_tick = self._find_peak_tick(
                candidates=candidates,
                liquidity_curve=liquidity_curve,
                current_tick=current_tick,
            )
            return tick_to_price(peak_tick, pool.token0_decimals, pool.token1_decimals)

        if method == "avg_liquidity_in_range":
            avg_tick = self._find_weighted_avg_tick(
                candidates=candidates,
                liquidity_curve=liquidity_curve,
            )
            if avg_tick is None:
                if warnings is not None:
                    warnings.append(
                        "Weighted average liquidity is non-positive in range; using current price."
                    )
                logger.warning(
                    "simulate_apr: weighted average liquidity non-positive for range [%s, %s], using current price",
                    tick_lower,
                    tick_upper,
                )
                return current_price
            return tick_to_price(avg_tick, pool.token0_decimals, pool.token1_decimals)

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
        current_tick: int,
    ) -> int:
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
            raise InvalidSimulationInputError("Could not determine peak tick.")
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
