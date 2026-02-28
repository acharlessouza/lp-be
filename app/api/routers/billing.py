from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.deps import (
    get_create_checkout_session_use_case,
    get_current_user,
    get_process_stripe_webhook_use_case,
)
from app.api.schemas.billing import (
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    StripeWebhookResponse,
)
from app.application.dto.billing import CreateCheckoutSessionInput, StripeWebhookInput
from app.application.use_cases.create_checkout_session import CreateCheckoutSessionUseCase
from app.application.use_cases.process_stripe_webhook import ProcessStripeWebhookUseCase
from app.domain.entities.user import User
from app.domain.exceptions import BillingError
from app.shared.config import get_settings


router = APIRouter()


@router.post("/v1/billing/checkout-session", response_model=CreateCheckoutSessionResponse)
def create_checkout_session(
    req: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    use_case: CreateCheckoutSessionUseCase = Depends(get_create_checkout_session_use_case),
):
    settings = get_settings()
    if not settings.stripe_success_url or not settings.stripe_cancel_url:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_SUCCESS_URL and STRIPE_CANCEL_URL are required.",
        )
    try:
        output = use_case.execute(
            CreateCheckoutSessionInput(
                user_id=current_user.id,
                plan_price_id=req.plan_price_id,
                success_url=settings.stripe_success_url,
                cancel_url=settings.stripe_cancel_url,
            )
        )
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateCheckoutSessionResponse(
        checkout_session_id=output.checkout_session_id,
        checkout_url=output.checkout_url,
    )


@router.post("/v1/billing/webhook", response_model=StripeWebhookResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
    use_case: ProcessStripeWebhookUseCase = Depends(get_process_stripe_webhook_use_case),
):
    payload = await request.body()
    try:
        output = use_case.execute(
            StripeWebhookInput(
                signature=stripe_signature,
                payload=payload,
            )
        )
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StripeWebhookResponse(event_type=output.event_type, handled=output.handled)
