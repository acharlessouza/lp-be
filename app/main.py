from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from .core.auth import require_jwt
from .core.config import get_settings
from .core.db import get_session_factory
from .schemas.allocation import AllocationRequest, AllocationResponse
from .repositories.pools import PoolRepository
from .services.allocation import AllocationService
from .services.pricing import CoingeckoPriceProvider, PriceLookupError, PriceOverrides, PriceService

app = FastAPI(title="LP API")

def get_price_service() -> PriceService:
    settings = get_settings()
    overrides = PriceOverrides(settings.price_overrides)
    coingecko = CoingeckoPriceProvider(
        api_base=settings.coingecko_api_base,
        timeout_seconds=settings.coingecko_timeout_seconds,
    )
    return PriceService(overrides=overrides, coingecko=coingecko)


def get_allocation_service() -> AllocationService:
    return AllocationService()


def get_pool_repository() -> PoolRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    session_factory = get_session_factory(settings.postgres_dsn)
    return PoolRepository(session_factory)


@app.post("/v1/allocate", response_model=AllocationResponse)
def allocate(
    req: AllocationRequest,
    _token: str = Depends(require_jwt),
    price_service: PriceService = Depends(get_price_service),
    allocation_service: AllocationService = Depends(get_allocation_service),
    pool_repo: PoolRepository = Depends(get_pool_repository),
):
    try:
        pools = pool_repo.get_by_address(req.pool_address, network=req.rede)
        if not pools:
            raise HTTPException(status_code=404, detail="Pool not found.")
        pool = pools[0]
        price0, price1 = price_service.get_pair_prices(
            token0=pool.token0_address,
            token1=pool.token1_address,
            network=pool.network,
        )
        result = allocation_service.allocate(
            deposit_usd=req.amount,
            price_token0_usd=price0,
            price_token1_usd=1,
            range_min=req.range1,
            range_max=req.range2,
        )
    except PriceLookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AllocationResponse(
        pool_id=pool.id,
        pool_address=pool.pool_address,
        rede=pool.network,
        taxa=pool.fee_tier,
        token0_address=pool.token0_address,
        token0_symbol=pool.token0_symbol,
        token1_address=pool.token1_address,
        token1_symbol=pool.token1_symbol,
        amount_token0=result.amount_token0,
        amount_token1=result.amount_token1,
        price_token0_usd=price0,
        price_token1_usd=price1,
    )
