from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from app.application.use_cases.create_checkout_session import CreateCheckoutSessionUseCase
from app.application.use_cases.get_me import GetMeUseCase
from app.application.use_cases.get_user_entitlements import GetUserEntitlementsUseCase
from app.application.use_cases.allocate import AllocateUseCase
from app.application.use_cases.discover_pools import DiscoverPoolsUseCase
from app.application.use_cases.estimate_fees import EstimateFeesUseCase
from app.application.use_cases.get_liquidity_distribution import GetLiquidityDistributionUseCase
from app.application.use_cases.get_liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeUseCase,
)
from app.application.use_cases.get_pool_by_address import GetPoolByAddressUseCase
from app.application.use_cases.get_pool_price import GetPoolPriceUseCase
from app.application.use_cases.get_pool_volume_history import GetPoolVolumeHistoryUseCase
from app.application.use_cases.list_exchange_network_pools import (
    ListExchangeNetworkPoolsUseCase,
)
from app.application.use_cases.list_exchange_network_tokens import (
    ListExchangeNetworkTokensUseCase,
)
from app.application.use_cases.list_exchange_networks import ListExchangeNetworksUseCase
from app.application.use_cases.list_exchanges import ListExchangesUseCase
from app.application.use_cases.login_google import LoginGoogleUseCase
from app.application.use_cases.login_local import LoginLocalUseCase
from app.application.use_cases.match_ticks import MatchTicksUseCase
from app.application.use_cases.logout_session import LogoutSessionUseCase
from app.application.use_cases.process_stripe_webhook import ProcessStripeWebhookUseCase
from app.application.use_cases.refresh_session import RefreshSessionUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.application.use_cases.simulate_apr import SimulateAprUseCase
from app.application.use_cases.simulate_apr_v2 import SimulateAprV2UseCase
from app.infrastructure.clients.allocation_price_provider import PriceServiceAdapter
from app.infrastructure.clients.univ3_subgraph_client import (
    Univ3SubgraphClient,
    Univ3SubgraphClientSettings,
)
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
from app.infrastructure.db.repositories.pool_runtime_metadata_repository import (
    SqlPoolRuntimeMetadataRepository,
)
from app.infrastructure.db.repositories.pool_volume_history_repository import (
    SqlPoolVolumeHistoryRepository,
)
from app.infrastructure.db.repositories.accounts_repository import SqlAccountsRepository
from app.infrastructure.db.repositories.simulate_apr_repository import SqlSimulateAprRepository
from app.infrastructure.db.repositories.simulate_apr_v2_repository import SqlSimulateAprV2Repository
from app.infrastructure.db.repositories.tick_snapshot_on_demand_repository import (
    SqlTickSnapshotOnDemandRepository,
)
from app.domain.entities.user import User
from app.domain.exceptions import FeatureAccessDeniedError
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


@lru_cache(maxsize=1)
def _get_univ3_subgraph_client() -> Univ3SubgraphClient:
    settings = get_settings()
    return Univ3SubgraphClient(
        Univ3SubgraphClientSettings(
            graph_gateway_base=settings.graph_gateway_base,
            graph_api_key=settings.graph_api_key,
            graph_subgraph_ids=settings.graph_subgraph_ids,
            graph_blocks_subgraph_ids=settings.graph_blocks_subgraph_ids,
            timeout_seconds=settings.graph_on_demand_timeout_seconds,
            max_retries=settings.graph_on_demand_max_retries,
            min_interval_ms=settings.graph_on_demand_min_interval_ms,
        )
    )


def _get_accounts_repository() -> SqlAccountsRepository:
    return SqlAccountsRepository(_get_db_engine())


@lru_cache(maxsize=1)
def _get_password_hasher() -> "PasswordHasher":
    from app.infrastructure.security.password_hasher import PasswordHasher

    return PasswordHasher()


@lru_cache(maxsize=1)
def _get_token_service() -> JwtTokenService:
    from app.infrastructure.security.token_service import JwtTokenService

    settings = get_settings()
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is required.")
    return JwtTokenService(
        jwt_secret=settings.jwt_secret,
        access_ttl_minutes=settings.jwt_access_ttl_minutes,
        refresh_ttl_days=settings.jwt_refresh_ttl_days,
    )


@lru_cache(maxsize=1)
def _get_google_oauth_client() -> GoogleOidcClient:
    from app.infrastructure.clients.google_oidc_client import GoogleOidcClient

    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is required.")
    return GoogleOidcClient(client_id=settings.google_client_id)


@lru_cache(maxsize=1)
def _get_stripe_client() -> StripeClient:
    from app.infrastructure.clients.stripe_client import StripeClient

    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is required.")
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET is required.")
    return StripeClient(
        secret_key=settings.stripe_secret_key,
        webhook_secret=settings.stripe_webhook_secret,
    )


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


def get_simulate_apr_v2_use_case() -> SimulateAprV2UseCase:
    settings = get_settings()
    db_engine = _get_db_engine()
    return SimulateAprV2UseCase(
        simulate_apr_v2_port=SqlSimulateAprV2Repository(db_engine),
        tick_snapshot_on_demand_port=SqlTickSnapshotOnDemandRepository(
            db_engine,
            subgraph_client=_get_univ3_subgraph_client(),
        ),
        pool_runtime_metadata_port=SqlPoolRuntimeMetadataRepository(db_engine),
        max_on_demand_combinations=settings.graph_on_demand_max_combinations,
    )


def get_pool_volume_history_use_case() -> GetPoolVolumeHistoryUseCase:
    return GetPoolVolumeHistoryUseCase(
        pool_volume_history_port=SqlPoolVolumeHistoryRepository(_get_db_engine())
    )


def get_register_user_use_case() -> RegisterUserUseCase:
    return RegisterUserUseCase(
        auth_port=_get_accounts_repository(),
        password_hasher=_get_password_hasher(),
    )


def get_login_local_use_case() -> LoginLocalUseCase:
    return LoginLocalUseCase(
        auth_port=_get_accounts_repository(),
        password_hasher=_get_password_hasher(),
        token_port=_get_token_service(),
    )


def get_login_google_use_case() -> LoginGoogleUseCase:
    return LoginGoogleUseCase(
        auth_port=_get_accounts_repository(),
        google_oauth_port=_get_google_oauth_client(),
        token_port=_get_token_service(),
    )


def get_refresh_session_use_case() -> RefreshSessionUseCase:
    return RefreshSessionUseCase(
        auth_port=_get_accounts_repository(),
        token_port=_get_token_service(),
    )


def get_logout_session_use_case() -> LogoutSessionUseCase:
    return LogoutSessionUseCase(
        auth_port=_get_accounts_repository(),
        token_port=_get_token_service(),
    )


def get_get_user_entitlements_use_case() -> GetUserEntitlementsUseCase:
    return GetUserEntitlementsUseCase(entitlements_port=_get_accounts_repository())


def get_get_me_use_case() -> GetMeUseCase:
    return GetMeUseCase(get_user_entitlements_use_case=get_get_user_entitlements_use_case())


def get_create_checkout_session_use_case() -> CreateCheckoutSessionUseCase:
    return CreateCheckoutSessionUseCase(
        auth_port=_get_accounts_repository(),
        entitlements_port=_get_accounts_repository(),
        stripe_port=_get_stripe_client(),
    )


def get_process_stripe_webhook_use_case() -> ProcessStripeWebhookUseCase:
    return ProcessStripeWebhookUseCase(
        auth_port=_get_accounts_repository(),
        entitlements_port=_get_accounts_repository(),
        stripe_port=_get_stripe_client(),
    )


def get_current_user(
    authorization: str = Header(...),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    token = authorization.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token.")

    token_service = _get_token_service()
    auth_port = _get_accounts_repository()

    try:
        payload = token_service.decode_access_token(token=token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = auth_port.get_user_by_id(user_id=payload.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive.")
    return user


def require_feature(feature_code: str):
    def _dependency(
        user: User = Depends(get_current_user),
        entitlements_use_case: GetUserEntitlementsUseCase = Depends(get_get_user_entitlements_use_case),
    ) -> User:
        entitlements = entitlements_use_case.execute(user_id=user.id)
        if not entitlements.boolean_features.get(feature_code, False):
            raise HTTPException(
                status_code=403,
                detail=str(FeatureAccessDeniedError(f"Feature '{feature_code}' is required.")),
            )
        return user

    return _dependency
