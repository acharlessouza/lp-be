from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_allocate_use_case
from app.api.schemas.allocation import AllocationRequest, AllocationResponse
from app.application.dto.allocate import AllocateInput
from app.application.use_cases.allocate import AllocateUseCase
from app.api.auth import require_jwt
from app.domain.exceptions import AllocationInputError, PoolNotFoundError, PriceLookupDomainError

router = APIRouter()


@router.post("/v1/allocate", response_model=AllocationResponse)
def allocate(
    req: AllocationRequest,
    _token: str = Depends(require_jwt),
    use_case: AllocateUseCase = Depends(get_allocate_use_case),
):
    try:
        result = use_case.execute(
            AllocateInput(
                pool_address=req.pool_address,
                network=req.rede,
                deposit_usd=req.amount,
                range_min=req.range1,
                range_max=req.range2,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (AllocationInputError, PriceLookupDomainError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AllocationResponse(
        pool_address=result.pool_address,
        rede=result.rede,
        taxa=result.taxa,
        token0_address=result.token0_address,
        token0_symbol=result.token0_symbol,
        token1_address=result.token1_address,
        token1_symbol=result.token1_symbol,
        amount_token0=result.amount_token0,
        amount_token1=result.amount_token1,
        price_token0_usd=result.price_token0_usd,
        price_token1_usd=result.price_token1_usd,
    )
