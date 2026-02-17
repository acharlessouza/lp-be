from __future__ import annotations

from decimal import Decimal

from app.application.dto.liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeInput,
    GetLiquidityDistributionDefaultRangeOutput,
)
from app.application.ports.liquidity_distribution_port import LiquidityDistributionPort
from app.application.use_cases.liquidity_distribution_pool_resolver import (
    resolve_liquidity_distribution_pool,
)
from app.domain.exceptions import LiquidityDistributionInputError, LiquidityDistributionNotFoundError
from app.domain.services.liquidity_distribution_default_range import (
    calculate_preset_range,
    tick_to_price,
)


FEE_TIER_TO_TICK_SPACING = {
    100: 1,
    500: 10,
    3000: 60,
    10000: 200,
}


class GetLiquidityDistributionDefaultRangeUseCase:
    def __init__(self, *, distribution_port: LiquidityDistributionPort):
        self._distribution_port = distribution_port

    def execute(
        self,
        command: GetLiquidityDistributionDefaultRangeInput,
    ) -> GetLiquidityDistributionDefaultRangeOutput:
        _ = command.snapshot_date
        if command.initial_price is not None and command.initial_price <= 0:
            raise LiquidityDistributionInputError("initial_price must be greater than zero.")
        preset = command.preset.strip().lower()

        pool = resolve_liquidity_distribution_pool(
            distribution_port=self._distribution_port,
            pool_id=command.pool_id,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )

        tick_spacing = pool.tick_spacing
        if tick_spacing is None and pool.fee_tier is not None:
            tick_spacing = FEE_TIER_TO_TICK_SPACING.get(pool.fee_tier)
        if tick_spacing is None or tick_spacing <= 0:
            raise LiquidityDistributionInputError("tick_spacing not found.")

        current_tick = command.center_tick
        if current_tick is None:
            current_tick = pool.pool_tick if pool.pool_tick is not None else pool.current_tick
        if current_tick is None:
            raise LiquidityDistributionNotFoundError("Pool current tick not found.")

        current_price: Decimal | None = command.initial_price
        if current_price is None:
            if (
                pool.current_price_token1_per_token0 is not None
                and pool.current_price_token1_per_token0 > 0
            ):
                current_price = pool.current_price_token1_per_token0
            else:
                current_price = Decimal(
                    str(
                        tick_to_price(
                            current_tick,
                            pool.token0_decimals,
                            pool.token1_decimals,
                        )
                    )
                )
        if current_price is None or current_price <= 0:
            raise LiquidityDistributionNotFoundError("Pool price not found.")

        try:
            min_price, max_price, min_tick, max_tick = calculate_preset_range(
                preset=preset,
                current_tick=current_tick,
                current_price=current_price,
                tick_spacing=tick_spacing,
                swapped_pair=command.swapped_pair,
                token0_decimals=pool.token0_decimals,
                token1_decimals=pool.token1_decimals,
            )
        except ValueError as exc:
            raise LiquidityDistributionInputError(str(exc)) from exc

        return GetLiquidityDistributionDefaultRangeOutput(
            min_price=min_price,
            max_price=max_price,
            min_tick=min_tick,
            max_tick=max_tick,
            tick_spacing=tick_spacing,
        )
