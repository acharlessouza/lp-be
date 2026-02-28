from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import text

from app.application.ports.auth_port import AuthPort
from app.application.ports.entitlements_port import EntitlementsPort
from app.infrastructure.db.mappers.accounts_mapper import (
    map_row_to_auth_identity,
    map_row_to_auth_session,
    map_row_to_plan,
    map_row_to_plan_feature_grant,
    map_row_to_plan_price,
    map_row_to_subscription,
    map_row_to_user,
)


class SqlAccountsRepository(AuthPort, EntitlementsPort):
    def __init__(self, engine):
        self._engine = engine

    def get_user_by_id(self, *, user_id: str):
        sql = """
            SELECT id, name, email, email_verified, is_active, stripe_customer_id, created_at, updated_at
            FROM public.users
            WHERE id = :user_id
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"user_id": user_id}).mappings().first()
        if row is None:
            return None
        return map_row_to_user(row)

    def get_user_by_email(self, *, email: str):
        sql = """
            SELECT id, name, email, email_verified, is_active, stripe_customer_id, created_at, updated_at
            FROM public.users
            WHERE lower(email) = :email
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"email": email.lower()}).mappings().first()
        if row is None:
            return None
        return map_row_to_user(row)

    def get_user_by_stripe_customer_id(self, *, stripe_customer_id: str):
        sql = """
            SELECT id, name, email, email_verified, is_active, stripe_customer_id, created_at, updated_at
            FROM public.users
            WHERE stripe_customer_id = :stripe_customer_id
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"stripe_customer_id": stripe_customer_id}).mappings().first()
        if row is None:
            return None
        return map_row_to_user(row)

    def create_user(
        self,
        *,
        user_id: str,
        name: str,
        email: str,
        email_verified: bool,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime,
    ):
        sql = """
            INSERT INTO public.users (
                id, name, email, email_verified, is_active, created_at, updated_at
            ) VALUES (
                :id, :name, :email, :email_verified, :is_active, :created_at, :updated_at
            )
            RETURNING id, name, email, email_verified, is_active, stripe_customer_id, created_at, updated_at
        """
        params = {
            "id": user_id,
            "name": name,
            "email": email,
            "email_verified": email_verified,
            "is_active": is_active,
            "created_at": created_at,
            "updated_at": updated_at,
        }
        with self._engine.begin() as conn:
            row = conn.execute(text(sql), params).mappings().one()
        return map_row_to_user(row)

    def update_user_email_verified(self, *, user_id: str, email_verified: bool) -> None:
        sql = """
            UPDATE public.users
            SET email_verified = :email_verified,
                updated_at = now()
            WHERE id = :user_id
        """
        with self._engine.begin() as conn:
            conn.execute(text(sql), {"user_id": user_id, "email_verified": email_verified})

    def update_user_stripe_customer_id(self, *, user_id: str, stripe_customer_id: str) -> None:
        sql = """
            UPDATE public.users
            SET stripe_customer_id = :stripe_customer_id,
                updated_at = now()
            WHERE id = :user_id
        """
        with self._engine.begin() as conn:
            conn.execute(
                text(sql),
                {
                    "user_id": user_id,
                    "stripe_customer_id": stripe_customer_id,
                },
            )

    def create_identity(
        self,
        *,
        identity_id: str,
        user_id: str,
        provider: str,
        provider_subject: str | None,
        password_hash: str | None,
        created_at: datetime,
    ):
        sql = """
            INSERT INTO public.auth_identities (
                id, user_id, provider, provider_subject, password_hash, created_at
            ) VALUES (
                :id, :user_id, :provider, :provider_subject, :password_hash, :created_at
            )
            RETURNING id, user_id, provider, provider_subject, password_hash, created_at
        """
        with self._engine.begin() as conn:
            row = conn.execute(
                text(sql),
                {
                    "id": identity_id,
                    "user_id": user_id,
                    "provider": provider,
                    "provider_subject": provider_subject,
                    "password_hash": password_hash,
                    "created_at": created_at,
                },
            ).mappings().one()
        return map_row_to_auth_identity(row)

    def get_identity_for_user_provider(self, *, user_id: str, provider: str):
        sql = """
            SELECT id, user_id, provider, provider_subject, password_hash, created_at
            FROM public.auth_identities
            WHERE user_id = :user_id
              AND provider = :provider
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "user_id": user_id,
                    "provider": provider,
                },
            ).mappings().first()
        if row is None:
            return None
        return map_row_to_auth_identity(row)

    def get_identity_by_provider_subject(self, *, provider: str, provider_subject: str):
        sql = """
            SELECT id, user_id, provider, provider_subject, password_hash, created_at
            FROM public.auth_identities
            WHERE provider = :provider
              AND provider_subject = :provider_subject
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "provider": provider,
                    "provider_subject": provider_subject,
                },
            ).mappings().first()
        if row is None:
            return None
        return map_row_to_auth_identity(row)

    def update_identity_provider_subject(self, *, identity_id: str, provider_subject: str) -> None:
        sql = """
            UPDATE public.auth_identities
            SET provider_subject = :provider_subject
            WHERE id = :identity_id
        """
        with self._engine.begin() as conn:
            conn.execute(
                text(sql),
                {
                    "identity_id": identity_id,
                    "provider_subject": provider_subject,
                },
            )

    def get_local_identity_by_email(self, *, email: str):
        sql = """
            SELECT
                u.id AS user_id,
                u.name,
                u.email,
                u.email_verified,
                u.is_active,
                u.stripe_customer_id,
                u.created_at AS user_created_at,
                u.updated_at AS user_updated_at,
                i.id AS identity_id,
                i.provider,
                i.provider_subject,
                i.password_hash,
                i.created_at AS identity_created_at
            FROM public.users u
            JOIN public.auth_identities i
              ON i.user_id = u.id
            WHERE lower(u.email) = :email
              AND i.provider = 'local'
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"email": email.lower()}).mappings().first()
        if row is None:
            return None

        user = map_row_to_user(
            {
                "id": row["user_id"],
                "name": row["name"],
                "email": row["email"],
                "email_verified": row["email_verified"],
                "is_active": row["is_active"],
                "stripe_customer_id": row["stripe_customer_id"],
                "created_at": row["user_created_at"],
                "updated_at": row["user_updated_at"],
            }
        )
        identity = map_row_to_auth_identity(
            {
                "id": row["identity_id"],
                "user_id": row["user_id"],
                "provider": row["provider"],
                "provider_subject": row["provider_subject"],
                "password_hash": row["password_hash"],
                "created_at": row["identity_created_at"],
            }
        )
        return user, identity

    def create_session(
        self,
        *,
        session_id: str,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        revoked_at: datetime | None,
        user_agent: str | None,
        ip: str | None,
        created_at: datetime,
    ):
        sql = """
            INSERT INTO public.auth_sessions (
                id, user_id, refresh_token_hash, expires_at, revoked_at, user_agent, ip, created_at
            ) VALUES (
                :id, :user_id, :refresh_token_hash, :expires_at, :revoked_at, :user_agent, :ip, :created_at
            )
            RETURNING id, user_id, refresh_token_hash, expires_at, revoked_at, user_agent, ip, created_at
        """
        params = {
            "id": session_id,
            "user_id": user_id,
            "refresh_token_hash": refresh_token_hash,
            "expires_at": expires_at,
            "revoked_at": revoked_at,
            "user_agent": user_agent,
            "ip": ip,
            "created_at": created_at,
        }
        with self._engine.begin() as conn:
            row = conn.execute(text(sql), params).mappings().one()
        return map_row_to_auth_session(row)

    def get_session_by_refresh_token_hash(self, *, refresh_token_hash: str):
        sql = """
            SELECT id, user_id, refresh_token_hash, expires_at, revoked_at, user_agent, ip, created_at
            FROM public.auth_sessions
            WHERE refresh_token_hash = :refresh_token_hash
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "refresh_token_hash": refresh_token_hash,
                },
            ).mappings().first()
        if row is None:
            return None
        return map_row_to_auth_session(row)

    def revoke_session(self, *, session_id: str, revoked_at: datetime) -> None:
        sql = """
            UPDATE public.auth_sessions
            SET revoked_at = :revoked_at
            WHERE id = :session_id
              AND revoked_at IS NULL
        """
        with self._engine.begin() as conn:
            conn.execute(text(sql), {"session_id": session_id, "revoked_at": revoked_at})

    def get_plan_by_code(self, *, code: str):
        sql = """
            SELECT id, code, name, description, is_active, sort_order
            FROM public.plans
            WHERE code = :code
              AND is_active = true
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"code": code}).mappings().first()
        if row is None:
            return None
        return map_row_to_plan(row)

    def get_plan_by_id(self, *, plan_id: str):
        sql = """
            SELECT id, code, name, description, is_active, sort_order
            FROM public.plans
            WHERE id = :plan_id
              AND is_active = true
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"plan_id": plan_id}).mappings().first()
        if row is None:
            return None
        return map_row_to_plan(row)

    def get_plan_price_by_id(self, *, plan_price_id: str):
        sql = """
            SELECT id, plan_id, interval, currency, amount_cents, is_active, external_price_id
            FROM public.plan_prices
            WHERE id = :plan_price_id
              AND is_active = true
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"plan_price_id": plan_price_id}).mappings().first()
        if row is None:
            return None
        return map_row_to_plan_price(row)

    def get_plan_price_by_external_price_id(self, *, external_price_id: str):
        sql = """
            SELECT id, plan_id, interval, currency, amount_cents, is_active, external_price_id
            FROM public.plan_prices
            WHERE external_price_id = :external_price_id
              AND is_active = true
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                text(sql),
                {
                    "external_price_id": external_price_id,
                },
            ).mappings().first()
        if row is None:
            return None
        return map_row_to_plan_price(row)

    def list_plan_feature_grants(self, *, plan_id: str):
        sql = """
            SELECT
                f.code AS feature_code,
                f.type AS feature_type,
                pf.is_enabled,
                pf.limit_value
            FROM public.plan_features pf
            JOIN public.features f
              ON f.id = pf.feature_id
            WHERE pf.plan_id = :plan_id
            ORDER BY f.code
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), {"plan_id": plan_id}).mappings().all()
        return [map_row_to_plan_feature_grant(row) for row in rows]

    def get_effective_subscription_for_user(self, *, user_id: str):
        sql = """
            SELECT
                id,
                user_id,
                plan_price_id,
                status,
                current_period_start,
                current_period_end,
                cancel_at_period_end,
                canceled_at,
                external_subscription_id,
                created_at,
                updated_at
            FROM public.subscriptions
            WHERE user_id = :user_id
              AND status IN ('active', 'trialing')
            ORDER BY COALESCE(current_period_end, updated_at) DESC, updated_at DESC
            LIMIT 1
        """
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), {"user_id": user_id}).mappings().first()
        if row is None:
            return None
        return map_row_to_subscription(row)

    def upsert_subscription_by_external_id(
        self,
        *,
        subscription_id: str,
        user_id: str,
        plan_price_id: str,
        status: str,
        current_period_start: datetime | None,
        current_period_end: datetime | None,
        cancel_at_period_end: bool,
        canceled_at: datetime | None,
        now: datetime,
    ):
        select_sql = """
            SELECT id
            FROM public.subscriptions
            WHERE external_subscription_id = :subscription_id
            LIMIT 1
        """
        with self._engine.begin() as conn:
            existing = conn.execute(
                text(select_sql),
                {
                    "subscription_id": subscription_id,
                },
            ).mappings().first()

            if existing is None:
                row = conn.execute(
                    text(
                        """
                        INSERT INTO public.subscriptions (
                            id,
                            user_id,
                            plan_price_id,
                            status,
                            current_period_start,
                            current_period_end,
                            cancel_at_period_end,
                            canceled_at,
                            external_subscription_id,
                            created_at,
                            updated_at
                        ) VALUES (
                            :id,
                            :user_id,
                            :plan_price_id,
                            :status,
                            :current_period_start,
                            :current_period_end,
                            :cancel_at_period_end,
                            :canceled_at,
                            :external_subscription_id,
                            :created_at,
                            :updated_at
                        )
                        RETURNING id, user_id, plan_price_id, status, current_period_start, current_period_end,
                                  cancel_at_period_end, canceled_at, external_subscription_id, created_at, updated_at
                        """
                    ),
                    {
                        "id": str(uuid4()),
                        "user_id": user_id,
                        "plan_price_id": plan_price_id,
                        "status": status,
                        "current_period_start": current_period_start,
                        "current_period_end": current_period_end,
                        "cancel_at_period_end": cancel_at_period_end,
                        "canceled_at": canceled_at,
                        "external_subscription_id": subscription_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                ).mappings().one()
                return map_row_to_subscription(row)

            row = conn.execute(
                text(
                    """
                    UPDATE public.subscriptions
                    SET user_id = :user_id,
                        plan_price_id = :plan_price_id,
                        status = :status,
                        current_period_start = :current_period_start,
                        current_period_end = :current_period_end,
                        cancel_at_period_end = :cancel_at_period_end,
                        canceled_at = :canceled_at,
                        updated_at = :updated_at
                    WHERE external_subscription_id = :external_subscription_id
                    RETURNING id, user_id, plan_price_id, status, current_period_start, current_period_end,
                              cancel_at_period_end, canceled_at, external_subscription_id, created_at, updated_at
                    """
                ),
                {
                    "user_id": user_id,
                    "plan_price_id": plan_price_id,
                    "status": status,
                    "current_period_start": current_period_start,
                    "current_period_end": current_period_end,
                    "cancel_at_period_end": cancel_at_period_end,
                    "canceled_at": canceled_at,
                    "updated_at": now,
                    "external_subscription_id": subscription_id,
                },
            ).mappings().one()
            return map_row_to_subscription(row)

    def cancel_subscription_by_external_id(
        self,
        *,
        subscription_id: str,
        status: str,
        canceled_at: datetime | None,
        now: datetime,
    ) -> None:
        sql = """
            UPDATE public.subscriptions
            SET status = :status,
                canceled_at = :canceled_at,
                cancel_at_period_end = false,
                updated_at = :updated_at
            WHERE external_subscription_id = :external_subscription_id
        """
        with self._engine.begin() as conn:
            result = conn.execute(
                text(sql),
                {
                    "status": status,
                    "canceled_at": canceled_at,
                    "updated_at": now,
                    "external_subscription_id": subscription_id,
                },
            )
        if result.rowcount == 0:
            raise ValueError("Subscription not found for external_subscription_id.")
