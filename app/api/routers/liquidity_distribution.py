from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_liquidity_distribution_use_case
from app.api.schemas.liquidity_distribution import (
    LiquidityDistributionPointResponse,
    LiquidityDistributionPoolResponse,
    LiquidityDistributionRequest,
    LiquidityDistributionResponse,
)
from app.application.dto.liquidity_distribution import GetLiquidityDistributionInput
from app.application.use_cases.get_liquidity_distribution import GetLiquidityDistributionUseCase
from app.domain.exceptions import (
    LiquidityDistributionInputError,
    LiquidityDistributionNotFoundError,
    PoolNotFoundError,
)

router = APIRouter()


@router.post("/v1/liquidity-distribution", response_model=LiquidityDistributionResponse)
def get_liquidity_distribution(
    req: LiquidityDistributionRequest,
    _token: str = Depends(require_jwt),
    use_case: GetLiquidityDistributionUseCase = Depends(get_liquidity_distribution_use_case),
):
    try:
        result = use_case.execute(
            GetLiquidityDistributionInput(
                pool_id=req.pool_id,
                snapshot_date=req.snapshot_date,
                current_tick=req.current_tick,
                center_tick=req.center_tick,
                tick_range=req.tick_range,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiquidityDistributionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiquidityDistributionInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LiquidityDistributionResponse(
        pool=LiquidityDistributionPoolResponse(
            token0=result.token0,
            token1=result.token1,
        ),
        current_tick=result.current_tick,
        data=[
            LiquidityDistributionPointResponse(
                tick=item.tick,
                liquidity=item.liquidity,
                price=item.price,
            )
            for item in result.data
        ],
    )
