from __future__ import annotations

from app.domain.entities.entitlements import UserEntitlements
from app.domain.entities.feature import PlanFeatureGrant


def build_user_entitlements(
    *,
    user_id: str,
    plan_code: str,
    grants: list[PlanFeatureGrant],
) -> UserEntitlements:
    boolean_features: dict[str, bool] = {}
    limits: dict[str, int] = {}

    for grant in grants:
        if grant.feature_type == "boolean":
            boolean_features[grant.feature_code] = bool(grant.is_enabled)
            continue

        if grant.feature_type == "limit":
            if grant.is_enabled and grant.limit_value is not None:
                limits[grant.feature_code] = int(grant.limit_value)
            else:
                limits[grant.feature_code] = 0

    return UserEntitlements(
        user_id=user_id,
        plan_code=plan_code,
        boolean_features=boolean_features,
        limits=limits,
    )
