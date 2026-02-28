from __future__ import annotations

from pydantic import BaseModel


class MeUserResponse(BaseModel):
    id: str
    name: str
    email: str


class MeResponse(BaseModel):
    user: MeUserResponse
    plan_code: str
    features: dict[str, bool]
    limits: dict[str, int]
