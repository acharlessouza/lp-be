from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


FeatureType = Literal["boolean", "limit"]


@dataclass(frozen=True)
class Feature:
    id: str
    code: str
    name: str
    description: str | None
    type: FeatureType
    created_at: datetime


@dataclass(frozen=True)
class PlanFeatureGrant:
    feature_code: str
    feature_type: FeatureType
    is_enabled: bool
    limit_value: int | None
