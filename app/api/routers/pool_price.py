from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_pool_price_use_case
from app.api.schemas.pool_price import (
    PoolPricePointResponse,
    PoolPriceResponse,
    PoolPriceStatsResponse,
)
from app.application.dto.pool_price import GetPoolPriceInput
from app.application.use_cases.get_pool_price import GetPoolPriceUseCase
from app.domain.exceptions import PoolNotFoundError, PoolPriceInputError, PoolPriceNotFoundError

router = APIRouter()


def _dec_to_str_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


@router.get("/v1/pool-price", response_model=PoolPriceResponse)
def get_pool_price(
    pool_id: int,
    days: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    _token: str = Depends(require_jwt),
    use_case: GetPoolPriceUseCase = Depends(get_pool_price_use_case),
):
    try:
        result = use_case.execute(
            GetPoolPriceInput(
                pool_id=pool_id,
                days=days,
                start=start,
                end=end,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoolPriceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PoolPriceInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PoolPriceResponse(
        pool_id=result.pool_id,
        days=result.days,
        stats=PoolPriceStatsResponse(
            min=_dec_to_str_or_none(result.min_price),
            max=_dec_to_str_or_none(result.max_price),
            avg=_dec_to_str_or_none(result.avg_price),
            price=_dec_to_str_or_none(result.current_price),
        ),
        series=[
            PoolPricePointResponse(
                timestamp=row.timestamp.isoformat(),
                price=str(row.price),
            )
            for row in result.series
        ],
    )
