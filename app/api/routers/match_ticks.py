from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_match_ticks_use_case
from app.api.schemas.match_ticks import MatchTicksRequest, MatchTicksResponse
from app.application.dto.match_ticks import MatchTicksInput
from app.application.use_cases.match_ticks import MatchTicksUseCase
from app.domain.exceptions import MatchTicksInputError, PoolNotFoundError, PoolPriceNotFoundError

router = APIRouter()


@router.post("/v1/match-ticks", response_model=MatchTicksResponse)
def match_ticks(
    req: MatchTicksRequest,
    _token: str = Depends(require_jwt),
    use_case: MatchTicksUseCase = Depends(get_match_ticks_use_case),
):
    try:
        result = use_case.execute(
            MatchTicksInput(
                pool_id=req.pool_id,
                min_price=req.min_price,
                max_price=req.max_price,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoolPriceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MatchTicksInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MatchTicksResponse(
        min_price_matched=result.min_price_matched,
        max_price_matched=result.max_price_matched,
        current_price_matched=result.current_price_matched,
    )
