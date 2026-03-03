from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response

from app.api.deps import (
    get_forgot_password_use_case,
    get_login_google_use_case,
    get_login_local_use_case,
    get_logout_session_use_case,
    get_refresh_session_use_case,
    get_reset_password_use_case,
    get_register_user_use_case,
)
from app.api.schemas.auth import (
    AuthTokenResponse,
    ForgotPasswordRequest,
    GenericMessageResponse,
    LogoutResponse,
    GoogleLoginRequest,
    LoginRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ResetPasswordRequest,
)
from app.application.dto.auth import (
    LoginGoogleInput,
    LoginLocalInput,
    LogoutInput,
    RefreshSessionInput,
    RegisterUserInput,
)
from app.application.dto.password_reset import ForgotPasswordInput, ResetPasswordInput
from app.application.use_cases.forgot_password import ForgotPasswordUseCase
from app.application.use_cases.login_google import LoginGoogleUseCase
from app.application.use_cases.login_local import LoginLocalUseCase
from app.application.use_cases.logout_session import LogoutSessionUseCase
from app.application.use_cases.refresh_session import RefreshSessionUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.application.use_cases.reset_password import ResetPasswordUseCase
from app.domain.exceptions import (
    EmailAlreadyExistsError,
    GoogleTokenValidationError,
    InvalidCredentialsError,
    PasswordResetTokenInvalidError,
    RefreshSessionInvalidError,
    UserInactiveError,
)
from app.shared.config import get_settings


router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"


def _set_refresh_cookie(
    response: Response,
    refresh_token: str,
    max_age_seconds: int,
    expires_at: datetime,
) -> None:
    settings = get_settings()
    samesite = settings.auth_cookie_samesite
    if samesite not in {"lax", "strict", "none"}:
        raise HTTPException(status_code=500, detail="AUTH_COOKIE_SAMESITE must be lax, strict or none.")
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        samesite=samesite,
        secure=settings.auth_cookie_secure,
        domain=settings.auth_cookie_domain or None,
        max_age=max_age_seconds,
        expires=expires_at,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        domain=settings.auth_cookie_domain or None,
    )


def _cookie_max_age_seconds(refresh_expires_at: datetime) -> int:
    now = datetime.now(timezone.utc)
    return max(int((refresh_expires_at - now).total_seconds()), 0)


@router.post("/v1/auth/register", response_model=RegisterResponse)
def register_user(
    req: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(get_register_user_use_case),
):
    try:
        output = use_case.execute(
            RegisterUserInput(
                name=req.name,
                email=req.email,
                password=req.password,
            )
        )
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RegisterResponse(
        user={
            "id": output.user.id,
            "name": output.user.name,
            "email": output.user.email,
            "email_verified": output.user.email_verified,
            "is_active": output.user.is_active,
        }
    )


@router.post("/v1/auth/login", response_model=AuthTokenResponse)
def login_local(
    req: LoginRequest,
    response: Response,
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
    use_case: LoginLocalUseCase = Depends(get_login_local_use_case),
):
    try:
        output = use_case.execute(
            LoginLocalInput(
                email=req.email,
                password=req.password,
                user_agent=user_agent,
                ip=x_forwarded_for,
            )
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except UserInactiveError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    _set_refresh_cookie(
        response,
        output.refresh_token,
        max_age_seconds=_cookie_max_age_seconds(output.refresh_expires_at),
        expires_at=output.refresh_expires_at,
    )
    return AuthTokenResponse(
        access_token=output.access_token,
        access_expires_at=output.access_expires_at,
        refresh_expires_at=output.refresh_expires_at,
        user={
            "id": output.user.id,
            "name": output.user.name,
            "email": output.user.email,
            "email_verified": output.user.email_verified,
            "is_active": output.user.is_active,
        },
    )


@router.post("/v1/auth/google", response_model=AuthTokenResponse)
def login_google(
    req: GoogleLoginRequest,
    response: Response,
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
    use_case: LoginGoogleUseCase = Depends(get_login_google_use_case),
):
    try:
        output = use_case.execute(
            LoginGoogleInput(
                id_token=req.id_token,
                user_agent=user_agent,
                ip=x_forwarded_for,
            )
        )
    except GoogleTokenValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except UserInactiveError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    _set_refresh_cookie(
        response,
        output.refresh_token,
        max_age_seconds=_cookie_max_age_seconds(output.refresh_expires_at),
        expires_at=output.refresh_expires_at,
    )
    return AuthTokenResponse(
        access_token=output.access_token,
        access_expires_at=output.access_expires_at,
        refresh_expires_at=output.refresh_expires_at,
        user={
            "id": output.user.id,
            "name": output.user.name,
            "email": output.user.email,
            "email_verified": output.user.email_verified,
            "is_active": output.user.is_active,
        },
    )


@router.post("/v1/auth/refresh", response_model=RefreshTokenResponse)
def refresh_auth(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
    use_case: RefreshSessionUseCase = Depends(get_refresh_session_use_case),
):
    if not refresh_token_cookie:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie.")

    try:
        output = use_case.execute(
            RefreshSessionInput(
                refresh_token=refresh_token_cookie,
                user_agent=user_agent,
                ip=x_forwarded_for,
            )
        )
    except RefreshSessionInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except UserInactiveError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    _set_refresh_cookie(
        response,
        output.refresh_token,
        max_age_seconds=_cookie_max_age_seconds(output.refresh_expires_at),
        expires_at=output.refresh_expires_at,
    )
    return RefreshTokenResponse(
        access_token=output.access_token,
        access_expires_at=output.access_expires_at,
        refresh_expires_at=output.refresh_expires_at,
    )


@router.post("/v1/auth/logout", response_model=LogoutResponse)
def logout_auth(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    use_case: LogoutSessionUseCase = Depends(get_logout_session_use_case),
):
    if refresh_token_cookie:
        use_case.execute(LogoutInput(refresh_token=refresh_token_cookie))
    _clear_refresh_cookie(response)
    return LogoutResponse(message="Logged out")


@router.post("/v1/auth/password/forgot", response_model=GenericMessageResponse)
def forgot_password(
    req: ForgotPasswordRequest,
    user_agent: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
    use_case: ForgotPasswordUseCase = Depends(get_forgot_password_use_case),
):
    output = use_case.execute(
        ForgotPasswordInput(
            email=req.email,
            user_agent=user_agent,
            ip=x_forwarded_for,
        )
    )
    return GenericMessageResponse(message=output.message)


@router.post("/v1/auth/password/reset", response_model=GenericMessageResponse)
def reset_password(
    req: ResetPasswordRequest,
    use_case: ResetPasswordUseCase = Depends(get_reset_password_use_case),
):
    try:
        output = use_case.execute(
            ResetPasswordInput(
                token=req.token,
                new_password=req.new_password,
            )
        )
    except PasswordResetTokenInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GenericMessageResponse(message=output.message)
