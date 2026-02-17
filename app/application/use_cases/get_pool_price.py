from __future__ import annotations

from math import ceil

from app.application.dto.pool_price import GetPoolPriceInput, GetPoolPriceOutput
from app.application.ports.pool_price_port import PoolPricePort
from app.domain.exceptions import PoolNotFoundError, PoolPriceInputError, PoolPriceNotFoundError
from app.domain.services.pool_price import resolve_current_pool_price


class GetPoolPriceUseCase:
    def __init__(self, *, pool_price_port: PoolPricePort):
        self._pool_price_port = pool_price_port

    def execute(self, command: GetPoolPriceInput) -> GetPoolPriceOutput:
        if (command.start is None) != (command.end is None):
            raise PoolPriceInputError("start and end must be provided together.")

        if command.start is not None and command.end is not None:
            if command.days is not None:
                raise PoolPriceInputError("Use either days or start/end.")
            if command.start >= command.end:
                raise PoolPriceInputError("start must be earlier than end.")
        else:
            if command.days is None:
                raise PoolPriceInputError("days is required when start/end is not provided.")
            if command.days <= 0:
                raise PoolPriceInputError("days must be a positive integer.")
        if command.chain_id <= 0 or command.dex_id <= 0:
            raise PoolPriceInputError("chain_id and dex_id must be positive integers.")

        if not self._pool_price_port.pool_exists(
            pool_address=command.pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        ):
            raise PoolNotFoundError("Pool not found.")

        if command.start is not None and command.end is not None:
            stats = self._pool_price_port.get_stats_range(
                pool_address=command.pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                start=command.start,
                end=command.end,
            )
            series = self._pool_price_port.get_series_range(
                pool_address=command.pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                start=command.start,
                end=command.end,
            )
            days_value = int(ceil((command.end - command.start).total_seconds() / 86400))
        else:
            if command.days is None:
                raise PoolPriceInputError("days is required when start/end is not provided.")
            days_value = int(command.days)
            stats = self._pool_price_port.get_stats(
                pool_address=command.pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                days=days_value,
            )
            series = self._pool_price_port.get_series(
                pool_address=command.pool_address,
                chain_id=command.chain_id,
                dex_id=command.dex_id,
                days=days_value,
            )

        current = self._pool_price_port.get_latest_price(
            pool_address=command.pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
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

        return GetPoolPriceOutput(
            pool_address=command.pool_address,
            days=days_value,
            min_price=stats.min_price,
            max_price=stats.max_price,
            avg_price=stats.avg_price,
            current_price=current_price,
            series=series,
        )
