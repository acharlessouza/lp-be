from __future__ import annotations

from app.application.dto.liquidity_distribution import (
    GetLiquidityDistributionInput,
    GetLiquidityDistributionOutput,
    LiquidityDistributionPointOutput,
)
from app.application.ports.liquidity_distribution_port import LiquidityDistributionPort
from app.domain.exceptions import (
    LiquidityDistributionInputError,
    LiquidityDistributionNotFoundError,
    PoolNotFoundError,
)
from app.domain.services.liquidity_distribution import build_liquidity_distribution


class GetLiquidityDistributionUseCase:
    def __init__(self, *, distribution_port: LiquidityDistributionPort):
        self._distribution_port = distribution_port

    def execute(self, command: GetLiquidityDistributionInput) -> GetLiquidityDistributionOutput:
        if command.tick_range < 1:
            raise LiquidityDistributionInputError("tick_range must be >= 1.")

        pool = self._distribution_port.get_pool_by_id(pool_id=command.pool_id)
        if pool is None:
            raise PoolNotFoundError("Pool not found.")

        current_tick = command.center_tick if command.center_tick is not None else pool.current_tick
        if current_tick is None:
            raise LiquidityDistributionNotFoundError("Pool current tick not found.")

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

        return GetLiquidityDistributionOutput(
            token0=pool.token0_symbol,
            token1=pool.token1_symbol,
            current_tick=current_tick,
            data=[
                LiquidityDistributionPointOutput(
                    tick=tick,
                    liquidity=str(liquidity),
                    price=price,
                )
                for tick, liquidity, price in points
            ],
        )
