from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.auth import require_jwt
from .core.config import get_settings
from .core.db import get_engine
from .schemas.allocation import AllocationRequest, AllocationResponse
from .schemas.liquidity_distribution import (
    LiquidityDistributionPoint,
    LiquidityDistributionPool,
    LiquidityDistributionRequest,
    LiquidityDistributionResponse,
)
from .repositories.pools import PoolRepository
from .repositories.pool_price import PoolPriceRepository
from .repositories.liquidity_distribution import LiquidityDistributionRepository
from .services.allocation import AllocationService
from .services.pricing import CoingeckoPriceProvider, PriceLookupError, PriceOverrides, PriceService
from .services.subgraph import SubgraphError, UniswapV3SubgraphClient
from .schemas.pool_price import PoolPricePoint, PoolPriceResponse, PoolPriceStats

app = FastAPI(title="LP API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    engine = get_engine(settings.postgres_dsn)
    return PoolRepository(engine)


def get_liquidity_distribution_repository() -> LiquidityDistributionRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return LiquidityDistributionRepository(engine)


def get_pool_price_repository() -> PoolPriceRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return PoolPriceRepository(engine)


def get_subgraph_client() -> UniswapV3SubgraphClient:
    settings = get_settings()
    return UniswapV3SubgraphClient(
        graph_api_key=settings.graph_api_key,
        graph_gateway_base=settings.graph_gateway_base,
        subgraph_ids=settings.graph_subgraph_ids,
        timeout_seconds=settings.graph_request_timeout_seconds,
    )


def _dec_to_str(value) -> str:
    return str(value) if value is not None else ""


def _dec_to_str_or_none(value) -> str | None:
    return str(value) if value is not None else None


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


@app.post("/api/liquidity-distribution", response_model=LiquidityDistributionResponse)
@app.post("/v1/liquidity-distribution", response_model=LiquidityDistributionResponse)
def liquidity_distribution(
    req: LiquidityDistributionRequest,
    _token: str = Depends(require_jwt),
    pool_repo: PoolRepository = Depends(get_pool_repository),
    dist_repo: LiquidityDistributionRepository = Depends(get_liquidity_distribution_repository),
    subgraph_client: UniswapV3SubgraphClient = Depends(get_subgraph_client),
):
    pool = pool_repo.get_by_id(req.pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found.")
    try:
        current_tick = subgraph_client.get_current_tick(
            network=pool.network,
            pool_address=pool.pool_address,
        )
    except SubgraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    min_tick = current_tick - req.tick_range
    max_tick = current_tick + req.tick_range

    rows = dist_repo.get_rows(
        pool_id=pool.id,
        snapshot_date=req.snapshot_date,
        min_tick=min_tick,
        max_tick=max_tick,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Tick snapshot not found.")

    data_out = [
        LiquidityDistributionPoint(
            tick=row.tick_idx,
            liquidity=_dec_to_str(row.liquidity_active),
            price=float(row.price_token1_per_token0),
        )
        for row in rows
    ]

    return LiquidityDistributionResponse(
        pool=LiquidityDistributionPool(
            token0=pool.token0_symbol,
            token1=pool.token1_symbol,
        ),
        current_tick=current_tick,
        data=data_out,
    )


@app.get("/api/pool-price", response_model=PoolPriceResponse)
def pool_price(
    pool_id: int,
    days: int,
    _token: str = Depends(require_jwt),
    pool_repo: PoolRepository = Depends(get_pool_repository),
    price_repo: PoolPriceRepository = Depends(get_pool_price_repository),
    subgraph_client: UniswapV3SubgraphClient = Depends(get_subgraph_client),
):
    if days <= 0:
        raise HTTPException(status_code=400, detail="days must be a positive integer.")
    pool = pool_repo.get_by_id(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found.")

    stats_row = price_repo.get_stats(pool_id=pool.id, days=days)
    series_rows = price_repo.get_series(pool_id=pool.id, days=days)
    try:
        current_price = subgraph_client.get_current_price(
            network=pool.network,
            pool_address=pool.pool_address,
        )
    except SubgraphError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return PoolPriceResponse(
        pool_id=pool.id,
        days=days,
        stats=PoolPriceStats(
            min=_dec_to_str_or_none(stats_row.min_price),
            max=_dec_to_str_or_none(stats_row.max_price),
            avg=_dec_to_str_or_none(stats_row.avg_price),
            price=_dec_to_str_or_none(current_price),
        ),
        series=[
            PoolPricePoint(timestamp=row.timestamp.isoformat(), price=_dec_to_str(row.price))
            for row in series_rows
        ],
    )
