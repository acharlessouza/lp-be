from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_radar_pools_use_case
from app.api.schemas.radar_pools import RadarPoolResponseItem, RadarPoolsResponse
from app.application.dto.radar_pools import RadarPoolsInput
from app.application.use_cases.radar_pools import RadarPoolsUseCase
from app.domain.exceptions import RadarPoolsInputError

router = APIRouter()


@router.get("/v1/radar/pools", response_model=RadarPoolsResponse)
def radar_pools(
    network_id: int | None = None,
    exchange_id: int | None = None,
    token_symbol: str | None = None,
    timeframe_days: int = 14,
    page: int = 1,
    page_size: int = 10,
    order_by: str = "average_apr",
    order_dir: str = "desc",
    _token: str = Depends(require_jwt),
    use_case: RadarPoolsUseCase = Depends(get_radar_pools_use_case),
):
    try:
        result = use_case.execute(
            RadarPoolsInput(
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
    except RadarPoolsInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RadarPoolsResponse(
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        data=[
            RadarPoolResponseItem(
                pool_id=item.pool_id,
                pool_address=item.pool_address,
                pool_name=item.pool_name,
                network=item.network,
                exchange=item.exchange,
                dex_id=item.dex_id,
                chain_id=item.chain_id,
                token0_address=item.token0_address,
                token1_address=item.token1_address,
                token0_symbol=item.token0_symbol,
                token1_symbol=item.token1_symbol,
                token0_icon_url=item.token0_icon_url,
                token1_icon_url=item.token1_icon_url,
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
