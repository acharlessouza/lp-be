from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text


def seed_accounts_defaults(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO public.plans (id, code, name, description, is_active, sort_order)
                VALUES (:id, :code, :name, :description, true, :sort_order)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_active = EXCLUDED.is_active,
                    sort_order = EXCLUDED.sort_order
                """
            ),
            {
                "id": str(uuid4()),
                "code": "free",
                "name": "Free",
                "description": "Plano gratuito",
                "sort_order": 0,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO public.plans (id, code, name, description, is_active, sort_order)
                VALUES (:id, :code, :name, :description, true, :sort_order)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_active = EXCLUDED.is_active,
                    sort_order = EXCLUDED.sort_order
                """
            ),
            {
                "id": str(uuid4()),
                "code": "pro",
                "name": "Pro",
                "description": "Plano pago",
                "sort_order": 10,
            },
        )

        free_plan_id = conn.execute(
            text("SELECT id FROM public.plans WHERE code = 'free' LIMIT 1")
        ).scalar_one()
        pro_plan_id = conn.execute(
            text("SELECT id FROM public.plans WHERE code = 'pro' LIMIT 1")
        ).scalar_one()

        conn.execute(
            text(
                """
                INSERT INTO public.plan_prices (id, plan_id, interval, currency, amount_cents, is_active, external_price_id)
                VALUES (:id, :plan_id, :interval, :currency, :amount_cents, true, :external_price_id)
                ON CONFLICT (external_price_id) DO UPDATE
                SET plan_id = EXCLUDED.plan_id,
                    interval = EXCLUDED.interval,
                    currency = EXCLUDED.currency,
                    amount_cents = EXCLUDED.amount_cents,
                    is_active = EXCLUDED.is_active
                """
            ),
            {
                "id": str(uuid4()),
                "plan_id": str(free_plan_id),
                "interval": "month",
                "currency": "brl",
                "amount_cents": 0,
                "external_price_id": "price_free_month",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO public.plan_prices (id, plan_id, interval, currency, amount_cents, is_active, external_price_id)
                VALUES (:id, :plan_id, :interval, :currency, :amount_cents, true, :external_price_id)
                ON CONFLICT (external_price_id) DO UPDATE
                SET plan_id = EXCLUDED.plan_id,
                    interval = EXCLUDED.interval,
                    currency = EXCLUDED.currency,
                    amount_cents = EXCLUDED.amount_cents,
                    is_active = EXCLUDED.is_active
                """
            ),
            {
                "id": str(uuid4()),
                "plan_id": str(pro_plan_id),
                "interval": "month",
                "currency": "brl",
                "amount_cents": 9900,
                "external_price_id": "price_pro_month",
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO public.plan_prices (id, plan_id, interval, currency, amount_cents, is_active, external_price_id)
                VALUES (:id, :plan_id, :interval, :currency, :amount_cents, true, :external_price_id)
                ON CONFLICT (external_price_id) DO UPDATE
                SET plan_id = EXCLUDED.plan_id,
                    interval = EXCLUDED.interval,
                    currency = EXCLUDED.currency,
                    amount_cents = EXCLUDED.amount_cents,
                    is_active = EXCLUDED.is_active
                """
            ),
            {
                "id": str(uuid4()),
                "plan_id": str(pro_plan_id),
                "interval": "year",
                "currency": "brl",
                "amount_cents": 99000,
                "external_price_id": "price_pro_year",
            },
        )

        for feature in (
            {
                "code": "charts_advanced",
                "name": "Charts Avancados",
                "description": "Acesso a graficos avancados",
                "type": "boolean",
            },
            {
                "code": "export_csv",
                "name": "Exportacao CSV",
                "description": "Exportar dados em CSV",
                "type": "boolean",
            },
            {
                "code": "api_calls",
                "name": "Limite de chamadas API",
                "description": "Quantidade mensal de chamadas",
                "type": "limit",
            },
        ):
            conn.execute(
                text(
                    """
                    INSERT INTO public.features (id, code, name, description, type, created_at)
                    VALUES (:id, :code, :name, :description, :type, now())
                    ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        type = EXCLUDED.type
                    """
                ),
                {
                    "id": str(uuid4()),
                    "code": feature["code"],
                    "name": feature["name"],
                    "description": feature["description"],
                    "type": feature["type"],
                },
            )

        feature_ids = {
            row["code"]: row["id"]
            for row in conn.execute(text("SELECT id, code FROM public.features")).mappings().all()
        }

        assignments = (
            (str(free_plan_id), feature_ids["charts_advanced"], False, None),
            (str(free_plan_id), feature_ids["export_csv"], False, None),
            (str(free_plan_id), feature_ids["api_calls"], True, 100),
            (str(pro_plan_id), feature_ids["charts_advanced"], True, None),
            (str(pro_plan_id), feature_ids["export_csv"], True, None),
            (str(pro_plan_id), feature_ids["api_calls"], True, 10000),
        )
        for plan_id, feature_id, is_enabled, limit_value in assignments:
            conn.execute(
                text(
                    """
                    INSERT INTO public.plan_features (plan_id, feature_id, is_enabled, limit_value)
                    VALUES (:plan_id, :feature_id, :is_enabled, :limit_value)
                    ON CONFLICT (plan_id, feature_id) DO UPDATE
                    SET is_enabled = EXCLUDED.is_enabled,
                        limit_value = EXCLUDED.limit_value
                    """
                ),
                {
                    "plan_id": plan_id,
                    "feature_id": str(feature_id),
                    "is_enabled": is_enabled,
                    "limit_value": limit_value,
                },
            )
