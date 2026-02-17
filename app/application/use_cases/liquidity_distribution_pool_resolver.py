from __future__ import annotations

from app.application.ports.liquidity_distribution_port import LiquidityDistributionPort
from app.domain.entities.liquidity_distribution import LiquidityDistributionPool
from app.domain.exceptions import LiquidityDistributionInputError, PoolNotFoundError


def resolve_liquidity_distribution_pool(
    *,
    distribution_port: LiquidityDistributionPort,
    pool_id: int | str,
    chain_id: int | None,
    dex_id: int | None,
) -> LiquidityDistributionPool:
    if isinstance(pool_id, int):
        pool = distribution_port.get_pool_by_id(pool_id=pool_id)
        if pool is None:
            raise PoolNotFoundError("Pool not found.")
        return pool

    pool_address = pool_id.strip().lower()
    if not pool_address.startswith("0x"):
        raise LiquidityDistributionInputError("pool_id string must be a valid pool_address.")

    pools = distribution_port.find_pools_by_address(
        pool_address=pool_address,
        chain_id=chain_id,
        dex_id=dex_id,
    )
    if not pools:
        raise PoolNotFoundError("Pool not found.")
    if len(pools) > 1 and (chain_id is None or dex_id is None):
        raise LiquidityDistributionInputError(
            "pool_address matches multiple pools; provide chain_id and dex_id."
        )
    if len(pools) > 1:
        raise LiquidityDistributionInputError(
            "pool_address still matches multiple pools for the provided chain_id/dex_id."
        )
    return pools[0]
