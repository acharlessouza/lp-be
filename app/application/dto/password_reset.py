from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForgotPasswordInput:
    email: str
    user_agent: str | None
    ip: str | None


@dataclass(frozen=True)
class ForgotPasswordOutput:
    message: str


@dataclass(frozen=True)
class ResetPasswordInput:
    token: str
    new_password: str


@dataclass(frozen=True)
class ResetPasswordOutput:
    message: str
