from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_get_me_use_case
from app.api.schemas.me import MeResponse
from app.application.use_cases.get_me import GetMeUseCase
from app.domain.entities.user import User


router = APIRouter()


@router.get("/v1/me", response_model=MeResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    use_case: GetMeUseCase = Depends(get_get_me_use_case),
):
    output = use_case.execute(user=current_user)
    return MeResponse(
        user={
            "id": output.user_id,
            "name": output.name,
            "email": output.email,
        },
        plan_code=output.plan_code,
        features=output.boolean_features,
        limits=output.limits,
    )
