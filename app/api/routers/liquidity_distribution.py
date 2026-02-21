from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import (
    get_liquidity_distribution_default_range_use_case,
    get_liquidity_distribution_use_case,
)
from app.api.schemas.liquidity_distribution import (
    LiquidityDistributionDefaultRangeRequest,
    LiquidityDistributionDefaultRangeResponse,
    LiquidityDistributionPointResponse,
    LiquidityDistributionPoolResponse,
    LiquidityDistributionRequest,
    LiquidityDistributionResponse,
)
from app.application.dto.liquidity_distribution import GetLiquidityDistributionInput
from app.application.dto.liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeInput,
)
from app.application.use_cases.get_liquidity_distribution_default_range import (
    GetLiquidityDistributionDefaultRangeUseCase,
)
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
                chain_id=req.chain_id,
                dex_id=req.dex_id,
                snapshot_date=req.snapshot_date,
                current_tick=req.current_tick,
                center_tick=req.center_tick,
                tick_range=req.tick_range,
                range_min=req.range_min,
                range_max=req.range_max,
                swapped_pair=req.swapped_pair,
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


@router.post(
    "/v1/liquidity-distribution/default-range",
    response_model=LiquidityDistributionDefaultRangeResponse,
)
def get_liquidity_distribution_default_range(
    req: LiquidityDistributionDefaultRangeRequest,
    _token: str = Depends(require_jwt),
    use_case: GetLiquidityDistributionDefaultRangeUseCase = Depends(
        get_liquidity_distribution_default_range_use_case
    ),
):
    try:
        result = use_case.execute(
            GetLiquidityDistributionDefaultRangeInput(
                pool_id=req.pool_id,
                chain_id=req.chain_id,
                dex_id=req.dex_id,
                snapshot_date=req.snapshot_date,
                preset=req.preset,
                initial_price=Decimal(str(req.initial_price)) if req.initial_price is not None else None,
                center_tick=req.center_tick,
                swapped_pair=req.swapped_pair,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiquidityDistributionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LiquidityDistributionInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LiquidityDistributionDefaultRangeResponse(
        min_price=result.min_price,
        max_price=result.max_price,
        min_tick=result.min_tick,
        max_tick=result.max_tick,
        tick_spacing=result.tick_spacing,
    )
