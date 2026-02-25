from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_simulate_apr_v2_use_case
from app.api.schemas.simulate_apr_v2 import (
    SimulateAprV2Request,
    SimulateAprV2Response,
)
from app.application.dto.simulate_apr_v2 import SimulateAprV2Input
from app.application.use_cases.simulate_apr_v2 import SimulateAprV2UseCase
from app.domain.exceptions import (
    InvalidSimulationInputError,
    PoolNotFoundError,
    SimulationDataNotFoundError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/v2/simulate/apr", response_model=SimulateAprV2Response)
def simulate_apr_v2(
    req: SimulateAprV2Request,
    _token: str = Depends(require_jwt),
    use_case: SimulateAprV2UseCase = Depends(get_simulate_apr_v2_use_case),
):
    try:
        result = use_case.execute(
            SimulateAprV2Input(
                pool_address=req.pool_address,
                chain_id=req.chain_id,
                dex_id=req.dex_id,
                deposit_usd=req.deposit_usd,
                amount_token0=req.amount_token0,
                amount_token1=req.amount_token1,
                full_range=req.full_range,
                tick_lower=None,
                tick_upper=None,
                min_price=req.min_price,
                max_price=req.max_price,
                horizon="7d",
                lookback_days=req.lookback_days,
                calculation_method=req.calculation_method,
                custom_calculation_price=req.custom_calculation_price,
                apr_method="exact",
                swapped_pair=req.swapped_pair,
            )
        )
    except PoolNotFoundError as exc:
        logger.warning(
            "simulate_apr_v2_router: pool_not_found pool=%s chain_id=%s dex_id=%s detail=%s",
            req.pool_address,
            req.chain_id,
            req.dex_id,
            exc,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SimulationDataNotFoundError as exc:
        logger.warning(
            "simulate_apr_v2_router: data_not_found pool=%s chain_id=%s dex_id=%s lookback_days=%s code=%s context=%s detail=%s",
            req.pool_address,
            req.chain_id,
            req.dex_id,
            req.lookback_days,
            exc.code,
            exc.context,
            exc,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "code": exc.code,
                "context": exc.context,
            },
        ) from exc
    except InvalidSimulationInputError as exc:
        logger.warning(
            "simulate_apr_v2_router: invalid_input pool=%s chain_id=%s dex_id=%s detail=%s",
            req.pool_address,
            req.chain_id,
            req.dex_id,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SimulateAprV2Response(
        estimated_fees_period_usd=result.estimated_fees_period_usd,
        estimated_fees_24h_usd=result.estimated_fees_24h_usd,
        monthly_usd=result.monthly_usd,
        yearly_usd=result.yearly_usd,
        fee_apr=result.fee_apr,
        meta={
            "block_a_number": result.meta.block_a_number,
            "block_b_number": result.meta.block_b_number,
            "ts_a": result.meta.ts_a,
            "ts_b": result.meta.ts_b,
            "seconds_delta": result.meta.seconds_delta,
            "used_price": result.meta.used_price,
            "warnings": result.meta.warnings,
        },
    )
