from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserEntitlementsOutput:
    user_id: str
    plan_code: str
    boolean_features: dict[str, bool]
    limits: dict[str, int]
