from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import (
    get_list_exchange_network_pools_use_case,
    get_list_exchange_network_tokens_use_case,
    get_list_exchange_networks_use_case,
    get_list_exchanges_use_case,
    get_pool_by_address_use_case,
)
from app.api.schemas.catalog import (
    ExchangeResponse,
    NetworkResponse,
    PoolDetailResponse,
    PoolSummaryResponse,
    TokenResponse,
)
from app.application.dto.catalog import (
    GetPoolByAddressInput,
    ListExchangeNetworkPoolsInput,
    ListExchangeNetworkTokensInput,
    ListExchangeNetworksInput,
)
from app.application.use_cases.get_pool_by_address import GetPoolByAddressUseCase
from app.application.use_cases.list_exchange_network_pools import (
    ListExchangeNetworkPoolsUseCase,
)
from app.application.use_cases.list_exchange_network_tokens import (
    ListExchangeNetworkTokensUseCase,
)
from app.application.use_cases.list_exchange_networks import ListExchangeNetworksUseCase
from app.application.use_cases.list_exchanges import ListExchangesUseCase
from app.domain.exceptions import PoolNotFoundError

router = APIRouter()


@router.get("/v1/exchanges", response_model=list[ExchangeResponse])
def list_exchanges(
    _token: str = Depends(require_jwt),
    use_case: ListExchangesUseCase = Depends(get_list_exchanges_use_case),
):
    rows = use_case.execute()
    return [ExchangeResponse(id=row.id, name=row.name) for row in rows]


@router.get("/v1/exchanges/{exchange_id}/networks", response_model=list[NetworkResponse])
def list_exchange_networks(
    exchange_id: int,
    _token: str = Depends(require_jwt),
    use_case: ListExchangeNetworksUseCase = Depends(get_list_exchange_networks_use_case),
):
    rows = use_case.execute(ListExchangeNetworksInput(exchange_id=exchange_id))
    return [NetworkResponse(id=row.id, name=row.name) for row in rows]


@router.get(
    "/v1/exchanges/{exchange_id}/networks/{network_id}/tokens",
    response_model=list[TokenResponse],
)
def list_exchange_network_tokens(
    exchange_id: int,
    network_id: int,
    token: str | None = None,
    _token: str = Depends(require_jwt),
    use_case: ListExchangeNetworkTokensUseCase = Depends(get_list_exchange_network_tokens_use_case),
):
    rows = use_case.execute(
        ListExchangeNetworkTokensInput(
            exchange_id=exchange_id,
            network_id=network_id,
            token_address=token,
        )
    )
    return [TokenResponse(address=row.address, symbol=row.symbol, decimals=row.decimals) for row in rows]


@router.get(
    "/v1/exchanges/{exchange_id}/networks/{network_id}/pools",
    response_model=list[PoolSummaryResponse],
)
def list_exchange_network_pools(
    exchange_id: int,
    network_id: int,
    token0: str,
    token1: str,
    _token: str = Depends(require_jwt),
    use_case: ListExchangeNetworkPoolsUseCase = Depends(get_list_exchange_network_pools_use_case),
):
    rows = use_case.execute(
        ListExchangeNetworkPoolsInput(
            exchange_id=exchange_id,
            network_id=network_id,
            token0_address=token0,
            token1_address=token1,
        )
    )
    return [PoolSummaryResponse(pool_address=row.pool_address, fee_tier=row.fee_tier) for row in rows]


@router.get("/v1/pools/by-address/{pool_address}", response_model=PoolDetailResponse)
def get_pool_by_address(
    pool_address: str,
    chain_id: int,
    exchange_id: int,
    _token: str = Depends(require_jwt),
    use_case: GetPoolByAddressUseCase = Depends(get_pool_by_address_use_case),
):
    try:
        row = use_case.execute(
            GetPoolByAddressInput(
                pool_address=pool_address,
                chain_id=chain_id,
                exchange_id=exchange_id,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PoolDetailResponse(
        id=row.id,
        dex_key=row.dex_key,
        dex_name=row.dex_name,
        dex_version=row.dex_version,
        chain_key=row.chain_key,
        chain_name=row.chain_name,
        fee_tier=row.fee_tier,
        token0_address=row.token0_address,
        token0_symbol=row.token0_symbol,
        token0_decimals=row.token0_decimals,
        token1_address=row.token1_address,
        token1_symbol=row.token1_symbol,
        token1_decimals=row.token1_decimals,
    )
