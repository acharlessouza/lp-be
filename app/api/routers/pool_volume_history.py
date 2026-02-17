from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import require_jwt
from app.api.deps import get_pool_volume_history_use_case
from app.api.schemas.pool_volume_history import (
    PoolVolumeHistoryPointResponse,
    PoolVolumeHistorySummaryResponse,
    PoolVolumeHistoryWithSummaryResponse,
)
from app.application.dto.pool_volume_history import GetPoolVolumeHistoryInput
from app.application.use_cases.get_pool_volume_history import GetPoolVolumeHistoryUseCase
from app.domain.exceptions import PoolVolumeHistoryInputError

router = APIRouter()


@router.get(
    "/v1/pools/{pool_address}/volume-history",
    response_model=PoolVolumeHistoryWithSummaryResponse,
)
def get_pool_volume_history(
    pool_address: str,
    days: int,
    chain_id: int | None = Query(default=None, alias="chainId"),
    dex_id: int | None = Query(default=None, alias="dexId"),
    include_premium: bool = Query(default=False, alias="includePremium"),
    exchange: str = Query(default="coingecko-derived"),
    symbol0: str | None = Query(default=None),
    symbol1: str | None = Query(default=None),
    _token: str = Depends(require_jwt),
    use_case: GetPoolVolumeHistoryUseCase = Depends(get_pool_volume_history_use_case),
):
    try:
        output = use_case.execute(
            GetPoolVolumeHistoryInput(
                pool_address=pool_address,
                days=days,
                chain_id=chain_id,
                dex_id=dex_id,
                include_premium=include_premium,
                exchange=exchange,
                symbol0=symbol0,
                symbol1=symbol1,
            )
        )
    except PoolVolumeHistoryInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    volume_history = [
        PoolVolumeHistoryPointResponse(
            time=row.time,
            value=row.value,
            fees_usd=row.fees_usd,
        )
        for row in output.volume_history
    ]
    return PoolVolumeHistoryWithSummaryResponse(
        volume_history=volume_history,
        summary=PoolVolumeHistorySummaryResponse(
            tvl_usd=output.summary.tvl_usd,
            avg_daily_fees_usd=output.summary.avg_daily_fees_usd,
            daily_fees_tvl_pct=output.summary.daily_fees_tvl_pct,
            avg_daily_volume_usd=output.summary.avg_daily_volume_usd,
            daily_volume_tvl_pct=output.summary.daily_volume_tvl_pct,
            price_volatility_pct=output.summary.price_volatility_pct,
            correlation=output.summary.correlation,
            geometric_mean_price=output.summary.geometric_mean_price,
        ),
    )
