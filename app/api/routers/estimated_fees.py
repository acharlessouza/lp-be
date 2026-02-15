from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_estimate_fees_use_case
from app.api.schemas.estimated_fees import (
    EstimatedFeesMonthlyResponse,
    EstimatedFeesRequest,
    EstimatedFeesResponse,
    EstimatedFeesYearlyResponse,
)
from app.application.dto.estimated_fees import EstimateFeesInput
from app.application.use_cases.estimate_fees import EstimateFeesUseCase
from app.domain.exceptions import PoolNotFoundError, PoolPriceInputError, PoolPriceNotFoundError

router = APIRouter()


@router.post("/v1/estimated-fees", response_model=EstimatedFeesResponse)
def estimate_fees(
    req: EstimatedFeesRequest,
    _token: str = Depends(require_jwt),
    use_case: EstimateFeesUseCase = Depends(get_estimate_fees_use_case),
):
    try:
        result = use_case.execute(
            EstimateFeesInput(
                pool_id=req.pool_id,
                days=req.days,
                min_price=req.min_price,
                max_price=req.max_price,
                deposit_usd=req.deposit_usd,
                amount_token0=req.amount_token0,
                amount_token1=req.amount_token1,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoolPriceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoolPriceInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return EstimatedFeesResponse(
        estimated_fees_24h=result.estimated_fees_24h,
        monthly=EstimatedFeesMonthlyResponse(
            value=result.monthly_value,
            percent=result.monthly_percent,
        ),
        yearly=EstimatedFeesYearlyResponse(
            value=result.yearly_value,
            apr=result.yearly_apr,
        ),
    )
