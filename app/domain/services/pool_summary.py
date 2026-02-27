from __future__ import annotations

from decimal import Decimal


def calculate_daily_tvl_pct(*, avg_daily_usd: Decimal | None, tvl_usd: Decimal | None) -> Decimal | None:
    if avg_daily_usd is None:
        return None
    if tvl_usd is None or tvl_usd <= 0:
        return None
    return (avg_daily_usd / tvl_usd) * Decimal("100")
