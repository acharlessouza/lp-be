from __future__ import annotations

from decimal import Decimal

from app.application.dto.estimated_fees import EstimateFeesInput, EstimateFeesOutput
from app.application.ports.estimated_fees_port import EstimatedFeesPort
from app.domain.exceptions import PoolNotFoundError, PoolPriceInputError, PoolPriceNotFoundError
from app.domain.services.estimated_fees import estimate_fees, position_liquidity
from app.domain.services.pool_price import resolve_current_pool_price


def _dec_or_zero(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


class EstimateFeesUseCase:
    def __init__(self, *, estimated_fees_port: EstimatedFeesPort):
        self._estimated_fees_port = estimated_fees_port

    def execute(self, command: EstimateFeesInput) -> EstimateFeesOutput:
        if command.days <= 0:
            raise PoolPriceInputError("days must be a positive integer.")

        pool = self._estimated_fees_port.get_pool_by_id(pool_id=command.pool_id)
        if pool is None:
            raise PoolNotFoundError("Pool not found.")

        aggregates = self._estimated_fees_port.get_aggregates(
            pool_id=command.pool_id,
            days=command.days,
            min_price=command.min_price,
            max_price=command.max_price,
        )

        pool_fees = _dec_or_zero(aggregates.pool_fees_in_range)
        avg_liquidity = _dec_or_zero(aggregates.avg_pool_liquidity_in_range)
        in_range_days = (
            Decimal(aggregates.hours_in_range) / Decimal("24")
            if aggregates.hours_in_range > 0
            else Decimal("0")
        )

        current = self._estimated_fees_port.get_latest_price(pool_id=command.pool_id)
        if current is None:
            raise PoolPriceNotFoundError("Pool price not found.")

        try:
            current_price = resolve_current_pool_price(
                token1_price=current.token1_price,
                token0_price=current.token0_price,
                sqrt_price_x96=current.sqrt_price_x96,
            )
        except ValueError as exc:
            detail = str(exc)
            if "not found" in detail.lower():
                raise PoolPriceNotFoundError(detail) from exc
            raise PoolPriceInputError(detail) from exc

        user_liquidity = position_liquidity(
            amount_token0=command.amount_token0,
            amount_token1=command.amount_token1,
            price_current=current_price,
            price_min=command.min_price,
            price_max=command.max_price,
            token0_decimals=pool.token0_decimals,
            token1_decimals=pool.token1_decimals,
        )

        calculated = estimate_fees(
            pool_fees=pool_fees,
            avg_liquidity=avg_liquidity,
            in_range_days=in_range_days,
            deposit_usd=command.deposit_usd,
            user_liquidity=user_liquidity,
        )

        return EstimateFeesOutput(
            estimated_fees_24h=calculated.estimated_fees_24h,
            monthly_value=calculated.monthly_value,
            monthly_percent=calculated.monthly_percent,
            yearly_value=calculated.yearly_value,
            yearly_apr=calculated.yearly_apr,
        )
