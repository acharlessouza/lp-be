from __future__ import annotations

from app.application.dto.match_ticks import MatchTicksInput, MatchTicksOutput
from app.application.ports.match_ticks_port import MatchTicksPort
from app.domain.exceptions import MatchTicksInputError, PoolNotFoundError, PoolPriceNotFoundError
from app.domain.services.match_ticks import match_prices


class MatchTicksUseCase:
    def __init__(self, *, match_ticks_port: MatchTicksPort):
        self._match_ticks_port = match_ticks_port

    def execute(self, command: MatchTicksInput) -> MatchTicksOutput:
        if command.min_price <= 0 or command.max_price <= 0:
            raise MatchTicksInputError("min_price and max_price must be positive.")
        if command.min_price >= command.max_price:
            raise MatchTicksInputError("min_price must be lower than max_price.")

        pool_config = self._match_ticks_port.get_pool_config(pool_id=command.pool_id)
        if pool_config is None:
            raise PoolNotFoundError("Pool not found.")

        latest_prices = self._match_ticks_port.get_latest_prices(pool_id=command.pool_id)
        if latest_prices is None:
            raise PoolPriceNotFoundError("Pool price not found.")

        current_price = latest_prices.token1_price
        if current_price is None and latest_prices.token0_price is not None:
            if latest_prices.token0_price == 0:
                raise MatchTicksInputError("Invalid pool price.")
            current_price = 1 / latest_prices.token0_price
        if current_price is None or current_price <= 0:
            raise MatchTicksInputError("Invalid pool price.")

        try:
            min_matched, max_matched, current_matched = match_prices(
                min_price=float(command.min_price),
                max_price=float(command.max_price),
                current_price=float(current_price),
                fee_tier=pool_config.fee_tier,
            )
        except ValueError as exc:
            raise MatchTicksInputError(str(exc)) from exc

        return MatchTicksOutput(
            min_price_matched=min_matched,
            max_price_matched=max_matched,
            current_price_matched=current_matched,
        )
