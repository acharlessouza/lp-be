from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from app.application.use_cases.allocate import AllocateUseCase
from app.application.use_cases.discover_pools import DiscoverPoolsUseCase
from app.application.use_cases.estimate_fees import EstimateFeesUseCase
from app.application.use_cases.get_liquidity_distribution import GetLiquidityDistributionUseCase
from app.application.use_cases.get_liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeUseCase,
)
from app.application.use_cases.get_pool_by_address import GetPoolByAddressUseCase
from app.application.use_cases.get_pool_price import GetPoolPriceUseCase
from app.application.use_cases.list_exchange_network_pools import (
    ListExchangeNetworkPoolsUseCase,
)
from app.application.use_cases.list_exchange_network_tokens import (
    ListExchangeNetworkTokensUseCase,
)
from app.application.use_cases.list_exchange_networks import ListExchangeNetworksUseCase
from app.application.use_cases.list_exchanges import ListExchangesUseCase
from app.application.use_cases.match_ticks import MatchTicksUseCase
from app.application.use_cases.simulate_apr import SimulateAprUseCase
from app.infrastructure.clients.allocation_price_provider import PriceServiceAdapter
from app.infrastructure.clients.pricing import CoingeckoPriceProvider, PriceOverrides, PriceService
from app.infrastructure.db.engine import get_engine
from app.infrastructure.db.repositories.allocation_pool_repository import (
    SqlAllocationPoolRepository,
)
from app.infrastructure.db.repositories.catalog_query_repository import SqlCatalogQueryRepository
from app.infrastructure.db.repositories.discover_pools_repository import SqlDiscoverPoolsRepository
from app.infrastructure.db.repositories.estimated_fees_repository import SqlEstimatedFeesRepository
from app.infrastructure.db.repositories.liquidity_distribution_repository import (
    SqlLiquidityDistributionRepository,
)
from app.infrastructure.db.repositories.match_ticks_repository import SqlMatchTicksRepository
from app.infrastructure.db.repositories.pool_price_repository import SqlPoolPriceRepository
from app.infrastructure.db.repositories.simulate_apr_repository import SqlSimulateAprRepository
from app.shared.config import get_settings


def _get_db_engine():
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    return get_engine(settings.postgres_dsn)


@lru_cache(maxsize=1)
def _get_price_service() -> PriceService:
    settings = get_settings()
    overrides = PriceOverrides(settings.price_overrides)
    coingecko = CoingeckoPriceProvider(
        api_base=settings.coingecko_api_base,
        timeout_seconds=settings.coingecko_timeout_seconds,
        cache_ttl_seconds=settings.coingecko_cache_ttl_seconds,
    )
    return PriceService(overrides=overrides, coingecko=coingecko)


def get_allocate_use_case() -> AllocateUseCase:
    pool_port = SqlAllocationPoolRepository(_get_db_engine())
    price_port = PriceServiceAdapter(_get_price_service())
    return AllocateUseCase(pool_port=pool_port, price_port=price_port)


def _get_catalog_query_repository() -> SqlCatalogQueryRepository:
    settings = get_settings()
    return SqlCatalogQueryRepository(
        engine=_get_db_engine(),
        min_tvl_usd=settings.pool_min_tvl_usd,
    )


def get_list_exchanges_use_case() -> ListExchangesUseCase:
    return ListExchangesUseCase(catalog_port=_get_catalog_query_repository())


def get_list_exchange_networks_use_case() -> ListExchangeNetworksUseCase:
    return ListExchangeNetworksUseCase(catalog_port=_get_catalog_query_repository())


def get_list_exchange_network_tokens_use_case() -> ListExchangeNetworkTokensUseCase:
    return ListExchangeNetworkTokensUseCase(catalog_port=_get_catalog_query_repository())


def get_list_exchange_network_pools_use_case() -> ListExchangeNetworkPoolsUseCase:
    return ListExchangeNetworkPoolsUseCase(catalog_port=_get_catalog_query_repository())


def get_pool_by_address_use_case() -> GetPoolByAddressUseCase:
    return GetPoolByAddressUseCase(catalog_port=_get_catalog_query_repository())


def get_pool_price_use_case() -> GetPoolPriceUseCase:
    return GetPoolPriceUseCase(pool_price_port=SqlPoolPriceRepository(_get_db_engine()))


def get_liquidity_distribution_use_case() -> GetLiquidityDistributionUseCase:
    settings = get_settings()
    return GetLiquidityDistributionUseCase(
        distribution_port=SqlLiquidityDistributionRepository(
            _get_db_engine(),
            min_tvl_usd=settings.pool_min_tvl_usd,
        )
    )


def get_liquidity_distribution_default_range_use_case() -> GetLiquidityDistributionDefaultRangeUseCase:
    settings = get_settings()
    return GetLiquidityDistributionDefaultRangeUseCase(
        distribution_port=SqlLiquidityDistributionRepository(
            _get_db_engine(),
            min_tvl_usd=settings.pool_min_tvl_usd,
        )
    )


def get_match_ticks_use_case() -> MatchTicksUseCase:
    return MatchTicksUseCase(match_ticks_port=SqlMatchTicksRepository(_get_db_engine()))


def get_estimate_fees_use_case() -> EstimateFeesUseCase:
    return EstimateFeesUseCase(estimated_fees_port=SqlEstimatedFeesRepository(_get_db_engine()))


def get_discover_pools_use_case() -> DiscoverPoolsUseCase:
    return DiscoverPoolsUseCase(discover_pools_port=SqlDiscoverPoolsRepository(_get_db_engine()))


def get_simulate_apr_use_case() -> SimulateAprUseCase:
    return SimulateAprUseCase(simulate_apr_port=SqlSimulateAprRepository(_get_db_engine()))
