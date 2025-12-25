from __future__ import annotations

from datetime import datetime
from decimal import Decimal, getcontext
from math import ceil

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.auth import require_jwt
from .core.config import get_settings
from .core.db import get_engine
from .schemas.allocation import AllocationRequest, AllocationResponse
from .schemas.estimated_fees import (
    EstimatedFeesMonthly,
    EstimatedFeesRequest,
    EstimatedFeesResponse,
    EstimatedFeesYearly,
)
from .schemas.liquidity_distribution import (
    LiquidityDistributionPoint,
    LiquidityDistributionPool,
    LiquidityDistributionRequest,
    LiquidityDistributionResponse,
)
from .repositories.estimated_fees import EstimatedFeesRepository
from .repositories.pools import PoolRepository
from .repositories.pool_price import PoolPriceRepository
from .repositories.liquidity_distribution import LiquidityDistributionRepository
from .repositories.exchanges import ExchangeRepository
from .repositories.current_price import CurrentPriceRepository
from .repositories.current_tick import CurrentTickRepository
from .repositories.networks import NetworkRepository
from .repositories.tokens import TokenRepository
from .repositories.match_ticks import MatchTicksRepository
from .services.allocation import AllocationService
from .services.current_price import resolve_current_price
from .services.current_tick import tick_from_sqrt_price_x96
from .services.match_ticks import match_prices
from .services.pricing import CoingeckoPriceProvider, PriceLookupError, PriceOverrides, PriceService
from .schemas.exchange import ExchangeResponse
from .schemas.network import NetworkResponse
from .schemas.token import TokenResponse
from .schemas.match_ticks import MatchTicksRequest, MatchTicksResponse
from .schemas.pool_price import PoolPricePoint, PoolPriceResponse, PoolPriceStats
from .schemas.pool_summary import PoolSummaryResponse
from .schemas.pool_detail import PoolDetailResponse

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


def get_estimated_fees_repository() -> EstimatedFeesRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return EstimatedFeesRepository(engine)


def get_pool_price_repository() -> PoolPriceRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return PoolPriceRepository(engine)


def get_exchange_repository() -> ExchangeRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return ExchangeRepository(engine)


def get_network_repository() -> NetworkRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return NetworkRepository(engine)


def get_token_repository() -> TokenRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return TokenRepository(engine)


def get_current_price_repository() -> CurrentPriceRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return CurrentPriceRepository(engine)


def get_current_tick_repository() -> CurrentTickRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return CurrentTickRepository(engine)


def get_match_ticks_repository() -> MatchTicksRepository:
    settings = get_settings()
    if not settings.postgres_dsn:
        raise HTTPException(status_code=500, detail="POSTGRES_DSN is required.")
    engine = get_engine(settings.postgres_dsn)
    return MatchTicksRepository(engine)


def _dec_to_str(value) -> str:
    return str(value) if value is not None else ""


def _dec_to_str_or_none(value) -> str | None:
    return str(value) if value is not None else None


def _dec_or_zero(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def _position_liquidity(
    *,
    amount_token0: Decimal,
    amount_token1: Decimal,
    price_current: Decimal,
    price_min: Decimal,
    price_max: Decimal,
    token0_decimals: int,
    token1_decimals: int,
) -> Decimal:
    if price_current <= 0 or price_min <= 0 or price_max <= 0:
        return Decimal("0")
    if price_min >= price_max:
        return Decimal("0")

    decimal_delta = token1_decimals - token0_decimals
    decimal_adjust = Decimal("10") ** Decimal(decimal_delta)
    price_current_raw = price_current * decimal_adjust
    price_min_raw = price_min * decimal_adjust
    price_max_raw = price_max * decimal_adjust
    amount0_raw = amount_token0 * (Decimal("10") ** Decimal(token0_decimals))
    amount1_raw = amount_token1 * (Decimal("10") ** Decimal(token1_decimals))

    ctx = getcontext()
    sa = price_min_raw.sqrt(ctx)
    sb = price_max_raw.sqrt(ctx)
    sp = price_current_raw.sqrt(ctx)

    if sp <= sa:
        denom = (Decimal("1") / sa) - (Decimal("1") / sb)
        return amount0_raw / denom if denom > 0 else Decimal("0")
    if sp >= sb:
        denom = sb - sa
        return amount1_raw / denom if denom > 0 else Decimal("0")

    amount0_per_l = (Decimal("1") / sp) - (Decimal("1") / sb)
    amount1_per_l = sp - sa
    liquidity0 = amount0_raw / amount0_per_l if amount0_per_l > 0 else Decimal("0")
    liquidity1 = amount1_raw / amount1_per_l if amount1_per_l > 0 else Decimal("0")
    if liquidity0 > 0 and liquidity1 > 0:
        return min(liquidity0, liquidity1)
    return liquidity0 if liquidity0 > 0 else liquidity1


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
    tick_repo: CurrentTickRepository = Depends(get_current_tick_repository),
):
    pool = pool_repo.get_by_id(req.pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found.")
    if req.center_tick is not None:
        current_tick = req.center_tick
    else:
        sqrt_price_x96 = tick_repo.get_latest_sqrt_price_x96(pool_id=pool.id)
        if sqrt_price_x96 is None:
            raise HTTPException(status_code=404, detail="Pool price not found.")
        try:
            current_tick = tick_from_sqrt_price_x96(sqrt_price_x96)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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


@app.post("/v1/match-ticks", response_model=MatchTicksResponse)
def match_ticks(
    req: MatchTicksRequest,
    _token: str = Depends(require_jwt),
    match_repo: MatchTicksRepository = Depends(get_match_ticks_repository),
):
    if req.min_price <= 0 or req.max_price <= 0:
        raise HTTPException(status_code=400, detail="min_price and max_price must be positive.")
    if req.min_price >= req.max_price:
        raise HTTPException(status_code=400, detail="min_price must be lower than max_price.")

    pool_config = match_repo.get_pool_config(pool_id=req.pool_id)
    if not pool_config:
        raise HTTPException(status_code=404, detail="Pool not found.")

    latest_prices = match_repo.get_latest_prices(pool_id=req.pool_id)
    if not latest_prices:
        raise HTTPException(status_code=404, detail="Pool price not found.")

    current_price = latest_prices.token1_price
    if current_price is None and latest_prices.token0_price is not None:
        if latest_prices.token0_price == 0:
            raise HTTPException(status_code=400, detail="Invalid pool price.")
        current_price = 1 / latest_prices.token0_price
    if current_price is None or current_price <= 0:
        raise HTTPException(status_code=400, detail="Invalid pool price.")

    try:
        min_matched, max_matched, current_matched = match_prices(
            min_price=float(req.min_price),
            max_price=float(req.max_price),
            current_price=float(current_price),
            fee_tier=pool_config.fee_tier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MatchTicksResponse(
        min_price_matched=min_matched,
        max_price_matched=max_matched,
        current_price_matched=current_matched,
    )


@app.get("/api/pool-price", response_model=PoolPriceResponse)
def pool_price(
    pool_id: int,
    days: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    _token: str = Depends(require_jwt),
    pool_repo: PoolRepository = Depends(get_pool_repository),
    price_repo: PoolPriceRepository = Depends(get_pool_price_repository),
    price_repo_current: CurrentPriceRepository = Depends(get_current_price_repository),
):
    if (start is None) != (end is None):
        raise HTTPException(status_code=400, detail="start and end must be provided together.")
    if start is not None and end is not None:
        if days is not None:
            raise HTTPException(status_code=400, detail="Use either days or start/end.")
        if start >= end:
            raise HTTPException(status_code=400, detail="start must be earlier than end.")
    else:
        if days is None:
            raise HTTPException(status_code=400, detail="days is required when start/end is not provided.")
        if days <= 0:
            raise HTTPException(status_code=400, detail="days must be a positive integer.")
    pool = pool_repo.get_by_id(pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found.")

    if start is not None and end is not None:
        stats_row = price_repo.get_stats_range(pool_id=pool.id, start=start, end=end)
        series_rows = price_repo.get_series_range(pool_id=pool.id, start=start, end=end)
        days_value = int(ceil((end - start).total_seconds() / 86400))
    else:
        stats_row = price_repo.get_stats(pool_id=pool.id, days=days)
        series_rows = price_repo.get_series(pool_id=pool.id, days=days)
        days_value = days
    current_row = price_repo_current.get_latest_price(pool_id=pool.id)
    if not current_row:
        raise HTTPException(status_code=404, detail="Pool price not found.")
    try:
        current_price = resolve_current_price(
            token1_price=current_row.token1_price,
            token0_price=current_row.token0_price,
            sqrt_price_x96=current_row.sqrt_price_x96,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    return PoolPriceResponse(
        pool_id=pool.id,
        days=days_value,
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


@app.post("/api/estimated-fees", response_model=EstimatedFeesResponse)
def estimated_fees(
    req: EstimatedFeesRequest,
    _token: str = Depends(require_jwt),
    pool_repo: PoolRepository = Depends(get_pool_repository),
    fees_repo: EstimatedFeesRepository = Depends(get_estimated_fees_repository),
    price_repo_current: CurrentPriceRepository = Depends(get_current_price_repository),
):
    if req.days <= 0:
        raise HTTPException(status_code=400, detail="days must be a positive integer.")
    pool = pool_repo.get_by_id(req.pool_id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found.")

    aggregates = fees_repo.get_aggregates(
        pool_id=req.pool_id,
        days=req.days,
        min_price=req.min_price,
        max_price=req.max_price,
    )

    pool_fees = _dec_or_zero(aggregates.pool_fees_in_range)
    avg_liquidity = _dec_or_zero(aggregates.avg_pool_liquidity_in_range)
    deposit_usd = req.deposit_usd
    hours_in_range = aggregates.hours_in_range
    in_range_days = Decimal(hours_in_range) / Decimal("24") if hours_in_range > 0 else Decimal("0")

    current_row = price_repo_current.get_latest_price(pool_id=pool.id)
    if not current_row:
        raise HTTPException(status_code=404, detail="Pool price not found.")
    try:
        current_price = resolve_current_price(
            token1_price=current_row.token1_price,
            token0_price=current_row.token0_price,
            sqrt_price_x96=current_row.sqrt_price_x96,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc

    user_liquidity = _position_liquidity(
        amount_token0=req.amount_token0,
        amount_token1=req.amount_token1,
        price_current=current_price,
        price_min=req.min_price,
        price_max=req.max_price,
        token0_decimals=pool.token0_decimals,
        token1_decimals=pool.token1_decimals,
    )

    if (
        deposit_usd <= 0
        or avg_liquidity <= 0
        or pool_fees <= 0
        or in_range_days <= 0
        or user_liquidity <= 0
    ):
        estimated_24h = Decimal("0")
        monthly_value = Decimal("0")
        monthly_percent = Decimal("0")
        yearly_value = Decimal("0")
        yearly_apr = Decimal("0")
    else:
        share = user_liquidity / avg_liquidity
        estimated_period = pool_fees * share
        estimated_24h = estimated_period / in_range_days
        monthly_value = estimated_24h * Decimal("30")
        yearly_value = estimated_24h * Decimal("365")
        monthly_percent = (monthly_value / deposit_usd) * Decimal("100")
        yearly_apr = yearly_value / deposit_usd

    return EstimatedFeesResponse(
        estimated_fees_24h=estimated_24h,
        monthly=EstimatedFeesMonthly(value=monthly_value, percent=monthly_percent),
        yearly=EstimatedFeesYearly(value=yearly_value, apr=yearly_apr),
    )


@app.get("/v1/exchanges", response_model=list[ExchangeResponse])
def list_exchanges(
    _token: str = Depends(require_jwt),
    exchange_repo: ExchangeRepository = Depends(get_exchange_repository),
):
    rows = exchange_repo.list_all()
    return [ExchangeResponse(id=row.id, name=row.name) for row in rows]


@app.get("/v1/exchanges/{exchange_id}/networks", response_model=list[NetworkResponse])
def list_exchange_networks(
    exchange_id: int,
    _token: str = Depends(require_jwt),
    network_repo: NetworkRepository = Depends(get_network_repository),
):
    rows = network_repo.list_by_exchange(exchange_id=exchange_id)
    return [NetworkResponse(id=row.id, name=row.name) for row in rows]


@app.get(
    "/v1/exchanges/{exchange_id}/networks/{network_id}/tokens",
    response_model=list[TokenResponse],
)
def list_exchange_network_tokens(
    exchange_id: int,
    network_id: int,
    token: str | None = None,
    _token: str = Depends(require_jwt),
    token_repo: TokenRepository = Depends(get_token_repository),
):
    rows = token_repo.list_by_exchange_network(
        exchange_id=exchange_id,
        network_id=network_id,
        token_address=token,
    )
    return [
        TokenResponse(address=row.address, symbol=row.symbol, decimals=row.decimals) for row in rows
    ]


@app.get(
    "/v1/exchanges/{exchange_id}/networks/{network_id}/pools",
    response_model=list[PoolSummaryResponse],
)
def list_exchange_network_pools(
    exchange_id: int,
    network_id: int,
    token0: str,
    token1: str,
    _token: str = Depends(require_jwt),
    pool_repo: PoolRepository = Depends(get_pool_repository),
):
    rows = pool_repo.list_by_exchange_network_tokens(
        exchange_id=exchange_id,
        network_id=network_id,
        token0_address=token0,
        token1_address=token1,
    )
    return [
        PoolSummaryResponse(
            pool_address=row.pool_address,
            fee_tier=row.fee_tier,
        )
        for row in rows
    ]


@app.get("/v1/pools/by-address/{pool_address}", response_model=PoolDetailResponse)
def get_pool_by_address(
    pool_address: str,
    network: str,
    exchange_id: int,
    _token: str = Depends(require_jwt),
    pool_repo: PoolRepository = Depends(get_pool_repository),
):
    pools = pool_repo.get_by_address(
        pool_address,
        network=network,
        exchange_id=exchange_id,
    )
    if not pools:
        raise HTTPException(status_code=404, detail="Pool not found.")
    pool = pools[0]
    return PoolDetailResponse(
        id=pool.id,
        fee_tier=pool.fee_tier,
        token0_address=pool.token0_address,
        token0_symbol=pool.token0_symbol,
        token0_decimals=pool.token0_decimals,
        token1_address=pool.token1_address,
        token1_symbol=pool.token1_symbol,
        token1_decimals=pool.token1_decimals,
    )
