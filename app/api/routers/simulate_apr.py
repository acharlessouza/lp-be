from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_jwt
from app.api.deps import get_simulate_apr_use_case
from app.api.schemas.simulate_apr import (
    SimulateAprDiagnosticsResponse,
    SimulateAprRequest,
    SimulateAprResponse,
)
from app.application.dto.simulate_apr import SimulateAprInput
from app.application.use_cases.simulate_apr import SimulateAprUseCase
from app.domain.exceptions import (
    InvalidSimulationInputError,
    PoolNotFoundError,
    SimulationDataNotFoundError,
)

router = APIRouter()


@router.post("/v1/simulate/apr", response_model=SimulateAprResponse)
def simulate_apr(
    req: SimulateAprRequest,
    _token: str = Depends(require_jwt),
    use_case: SimulateAprUseCase = Depends(get_simulate_apr_use_case),
):
    try:
        result = use_case.execute(
            SimulateAprInput(
                pool_address=req.pool_address,
                chain_id=req.chain_id,
                dex_id=req.dex_id,
                deposit_usd=req.deposit_usd,
                amount_token0=req.amount_token0,
                amount_token1=req.amount_token1,
                tick_lower=req.tick_lower,
                tick_upper=req.tick_upper,
                min_price=req.min_price,
                max_price=req.max_price,
                horizon=req.horizon,
                mode=req.mode,
                lookback_days=req.lookback_days,
            )
        )
    except PoolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SimulationDataNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidSimulationInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SimulateAprResponse(
        estimated_fees_24h_usd=result.estimated_fees_24h_usd,
        monthly_usd=result.monthly_usd,
        yearly_usd=result.yearly_usd,
        fee_apr=result.fee_apr,
        diagnostics=SimulateAprDiagnosticsResponse(
            hours_total=result.diagnostics.hours_total,
            hours_in_range=result.diagnostics.hours_in_range,
            percent_time_in_range=result.diagnostics.percent_time_in_range,
            avg_share_in_range=result.diagnostics.avg_share_in_range,
            assumptions=result.diagnostics.assumptions,
            warnings=result.diagnostics.warnings,
        ),
    )
