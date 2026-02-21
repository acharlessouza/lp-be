from __future__ import annotations

from app.application.dto.liquidity_distribution import (
    GetLiquidityDistributionInput,
    GetLiquidityDistributionOutput,
    LiquidityDistributionPointOutput,
)
from app.application.ports.liquidity_distribution_port import LiquidityDistributionPort
from app.application.use_cases.liquidity_distribution_pool_resolver import (
    resolve_liquidity_distribution_pool,
)
from app.domain.exceptions import (
    LiquidityDistributionInputError,
    LiquidityDistributionNotFoundError,
)
from app.domain.services.pair_orientation import invert_float_price
from app.domain.services.liquidity_distribution import build_liquidity_distribution


class GetLiquidityDistributionUseCase:
    def __init__(self, *, distribution_port: LiquidityDistributionPort):
        self._distribution_port = distribution_port

    def execute(self, command: GetLiquidityDistributionInput) -> GetLiquidityDistributionOutput:
        if command.tick_range < 1:
            raise LiquidityDistributionInputError("tick_range must be >= 1.")

        pool = resolve_liquidity_distribution_pool(
            distribution_port=self._distribution_port,
            pool_id=command.pool_id,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )

        current_tick = command.center_tick if command.center_tick is not None else pool.current_tick
        if current_tick is None:
            raise LiquidityDistributionNotFoundError("Pool current tick not found.")
        if command.swapped_pair and command.center_tick is not None:
            current_tick = -current_tick

        latest_period = self._distribution_port.get_latest_period_start(pool_id=pool.id)
        if latest_period is None:
            raise LiquidityDistributionNotFoundError("Tick snapshot not found.")

        rows = self._distribution_port.get_ticks_by_period(pool_id=pool.id, period_start=latest_period)
        if not rows:
            raise LiquidityDistributionNotFoundError("Tick snapshot not found.")

        if pool.onchain_liquidity is None:
            raise LiquidityDistributionNotFoundError("Pool liquidity not found.")

        min_tick = current_tick - command.tick_range
        max_tick = current_tick + command.tick_range

        points = build_liquidity_distribution(
            rows=rows,
            current_tick=current_tick,
            min_tick=min_tick,
            max_tick=max_tick,
            onchain_liquidity=pool.onchain_liquidity,
            token0_decimals=pool.token0_decimals,
            token1_decimals=pool.token1_decimals,
        )
        if not points:
            raise LiquidityDistributionNotFoundError("Tick snapshot not found.")

        output_points = [
            LiquidityDistributionPointOutput(
                tick=tick,
                liquidity=str(liquidity),
                price=price,
            )
            for tick, liquidity, price in points
        ]

        if not command.swapped_pair:
            return GetLiquidityDistributionOutput(
                token0=pool.token0_symbol,
                token1=pool.token1_symbol,
                current_tick=current_tick,
                data=output_points,
            )

        try:
            swapped_points = [
                LiquidityDistributionPointOutput(
                    tick=-item.tick,
                    liquidity=item.liquidity,
                    price=invert_float_price(item.price, field_name="price"),
                )
                for item in output_points
            ]
        except ValueError as exc:
            raise LiquidityDistributionInputError(str(exc)) from exc
        swapped_points.sort(key=lambda item: item.tick)

        return GetLiquidityDistributionOutput(
            token0=pool.token1_symbol,
            token1=pool.token0_symbol,
            current_tick=-current_tick,
            data=swapped_points,
        )
