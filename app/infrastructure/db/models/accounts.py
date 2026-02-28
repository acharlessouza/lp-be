from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.engine import Base


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class AuthIdentityModel(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_auth_identities_user_provider"),
        {"schema": "public"},
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class PlanModel(Base):
    __tablename__ = "plans"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class PlanPriceModel(Base):
    __tablename__ = "plan_prices"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.plans.id"), nullable=False)
    interval: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    external_price_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)


class FeatureModel(Base):
    __tablename__ = "features"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class PlanFeatureModel(Base):
    __tablename__ = "plan_features"
    __table_args__ = ({"schema": "public"},)

    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.plans.id"), primary_key=True)
    feature_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.features.id"), primary_key=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    limit_value: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"
    __table_args__ = ({"schema": "public"},)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.users.id"), nullable=False)
    plan_price_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("public.plan_prices.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
