from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_discover_pools_use_case
from app.api.schemas.discover_pools import DiscoverPoolResponseItem, DiscoverPoolsResponse
from app.application.dto.discover_pools import DiscoverPoolsInput
from app.application.use_cases.discover_pools import DiscoverPoolsUseCase
from app.domain.exceptions import DiscoverPoolsInputError

router = APIRouter()


@router.get("/v1/discover/pools", response_model=DiscoverPoolsResponse)
def discover_pools(
    network_id: int | None = None,
    exchange_id: int | None = None,
    token_symbol: str | None = None,
    timeframe_days: int = 14,
    page: int = 1,
    page_size: int = 10,
    order_by: str = "average_apr",
    order_dir: str = "desc",
    _token: str = Depends(require_jwt),
    use_case: DiscoverPoolsUseCase = Depends(get_discover_pools_use_case),
):
    try:
        result = use_case.execute(
            DiscoverPoolsInput(
                network_id=network_id,
                exchange_id=exchange_id,
                token_symbol=token_symbol,
                timeframe_days=timeframe_days,
                page=page,
                page_size=page_size,
                order_by=order_by,
                order_dir=order_dir,
            )
        )
    except DiscoverPoolsInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DiscoverPoolsResponse(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        data=[
            DiscoverPoolResponseItem(
                pool_id=item.pool_id,
                pool_address=item.pool_address,
                pool_name=item.pool_name,
                network=item.network,
                exchange=item.exchange,
                fee_tier=item.fee_tier,
                average_apr=item.average_apr,
                price_volatility=item.price_volatility,
                tvl_usd=item.tvl_usd,
                correlation=item.correlation,
                avg_daily_fees_usd=item.avg_daily_fees_usd,
                daily_fees_tvl_pct=item.daily_fees_tvl_pct,
                avg_daily_volume_usd=item.avg_daily_volume_usd,
                daily_volume_tvl_pct=item.daily_volume_tvl_pct,
            )
            for item in result.data
        ],
    )
