from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeOutput:
    user_id: str
    name: str
    email: str
    plan_code: str
    boolean_features: dict[str, bool]
    limits: dict[str, int]
