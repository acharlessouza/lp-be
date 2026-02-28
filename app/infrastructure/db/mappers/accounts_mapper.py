from __future__ import annotations

from typing import Any, Mapping

from app.domain.entities.feature import PlanFeatureGrant
from app.domain.entities.plan import Plan, PlanPrice
from app.domain.entities.subscription import Subscription
from app.domain.entities.user import AuthIdentity, AuthSession, User


def _as_str(value: Any) -> str:
    return str(value)


def map_row_to_user(row: Mapping[str, Any]) -> User:
    return User(
        id=_as_str(row["id"]),
        name=row["name"],
        email=row["email"],
        email_verified=bool(row["email_verified"]),
        is_active=bool(row["is_active"]),
        stripe_customer_id=row.get("stripe_customer_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def map_row_to_auth_identity(row: Mapping[str, Any]) -> AuthIdentity:
    return AuthIdentity(
        id=_as_str(row["id"]),
        user_id=_as_str(row["user_id"]),
        provider=row["provider"],
        provider_subject=row.get("provider_subject"),
        password_hash=row.get("password_hash"),
        created_at=row["created_at"],
    )


def map_row_to_auth_session(row: Mapping[str, Any]) -> AuthSession:
    return AuthSession(
        id=_as_str(row["id"]),
        user_id=_as_str(row["user_id"]),
        refresh_token_hash=row["refresh_token_hash"],
        expires_at=row["expires_at"],
        revoked_at=row.get("revoked_at"),
        user_agent=row.get("user_agent"),
        ip=row.get("ip"),
        created_at=row["created_at"],
    )


def map_row_to_plan(row: Mapping[str, Any]) -> Plan:
    return Plan(
        id=_as_str(row["id"]),
        code=row["code"],
        name=row["name"],
        description=row.get("description"),
        is_active=bool(row["is_active"]),
        sort_order=int(row["sort_order"]),
    )


def map_row_to_plan_price(row: Mapping[str, Any]) -> PlanPrice:
    return PlanPrice(
        id=_as_str(row["id"]),
        plan_id=_as_str(row["plan_id"]),
        interval=row["interval"],
        currency=row["currency"],
        amount_cents=int(row["amount_cents"]),
        is_active=bool(row["is_active"]),
        external_price_id=row.get("external_price_id"),
    )


def map_row_to_plan_feature_grant(row: Mapping[str, Any]) -> PlanFeatureGrant:
    return PlanFeatureGrant(
        feature_code=row["feature_code"],
        feature_type=row["feature_type"],
        is_enabled=bool(row["is_enabled"]),
        limit_value=int(row["limit_value"]) if row.get("limit_value") is not None else None,
    )


def map_row_to_subscription(row: Mapping[str, Any]) -> Subscription:
    return Subscription(
        id=_as_str(row["id"]),
        user_id=_as_str(row["user_id"]),
        plan_price_id=_as_str(row["plan_price_id"]),
        status=row["status"],
        current_period_start=row.get("current_period_start"),
        current_period_end=row.get("current_period_end"),
        cancel_at_period_end=bool(row["cancel_at_period_end"]),
        canceled_at=row.get("canceled_at"),
        external_subscription_id=row.get("external_subscription_id"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
