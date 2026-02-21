from __future__ import annotations

from app.application.dto.allocate import AllocateInput, AllocateOutput
from app.application.ports.allocation_pool_port import AllocationPoolPort
from app.application.ports.token_price_port import TokenPricePort
from app.domain.exceptions import AllocationInputError, PoolNotFoundError
from app.domain.services.pair_orientation import ui_price_range_to_canonical
from app.domain.services.allocation import split_deposit_full_range_equal_value, split_deposit_range


class AllocateUseCase:
    def __init__(self, *, pool_port: AllocationPoolPort, price_port: TokenPricePort):
        self._pool_port = pool_port
        self._price_port = price_port

    def execute(self, command: AllocateInput) -> AllocateOutput:
        pool = self._pool_port.get_by_address(
            pool_address=command.pool_address,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
        if pool is None:
            raise PoolNotFoundError("Pool not found.")

        price0, price1 = self._price_port.get_pair_prices(
            token0_address=pool.token0_address,
            token1_address=pool.token1_address,
            network=pool.network,
        )

        if command.full_range:
            amounts = split_deposit_full_range_equal_value(
                deposit_usd=command.deposit_usd,
                price_token0_usd=price0,
                price_token1_usd=price1,
            )
        else:
            if command.range_min is None or command.range_max is None:
                raise AllocationInputError("range1 and range2 are required when full_range is false.")

            range_min = command.range_min
            range_max = command.range_max
            if command.swapped_pair:
                range_min_ui = min(range_min, range_max)
                range_max_ui = max(range_min, range_max)
                try:
                    range_min, range_max = ui_price_range_to_canonical(
                        range_min_ui,
                        range_max_ui,
                        min_field_name="range1",
                        max_field_name="range2",
                    )
                except ValueError as exc:
                    raise AllocationInputError(str(exc)) from exc

            # Mantem o comportamento atual da API: alocacao por range usa token1 em 1 USD.
            amounts = split_deposit_range(
                deposit_usd=command.deposit_usd,
                price_token0_usd=price0,
                price_token1_usd=1,
                range_min=range_min,
                range_max=range_max,
            )

        if command.swapped_pair:
            return AllocateOutput(
                pool_address=pool.pool_address,
                rede=pool.network,
                taxa=pool.fee_tier,
                token0_address=pool.token1_address,
                token0_symbol=pool.token1_symbol,
                token1_address=pool.token0_address,
                token1_symbol=pool.token0_symbol,
                amount_token0=amounts.amount_token1,
                amount_token1=amounts.amount_token0,
                price_token0_usd=price1,
                price_token1_usd=price0,
            )

        return AllocateOutput(
            pool_address=pool.pool_address,
            rede=pool.network,
            taxa=pool.fee_tier,
            token0_address=pool.token0_address,
            token0_symbol=pool.token0_symbol,
            token1_address=pool.token1_address,
            token1_symbol=pool.token1_symbol,
            amount_token0=amounts.amount_token0,
            amount_token1=amounts.amount_token1,
            price_token0_usd=price0,
            price_token1_usd=price1,
        )
