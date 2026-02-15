from __future__ import annotations

from decimal import Decimal

from app.domain.entities.discover_pools import DiscoverPoolAggregate, DiscoverPoolItem


def decimal_or_zero(value: Decimal | None) -> Decimal:
    return value if value is not None else Decimal("0")


def build_discover_item(*, row: DiscoverPoolAggregate, timeframe_days: int) -> DiscoverPoolItem:
    tvl_usd = decimal_or_zero(row.avg_tvl_usd)
    avg_hourly_fees = decimal_or_zero(row.avg_hourly_fees_usd)
    avg_hourly_volume = decimal_or_zero(row.avg_hourly_volume_usd)
    total_fees = decimal_or_zero(row.total_fees_usd)

    avg_daily_fees_usd = avg_hourly_fees * Decimal("24")
    avg_daily_volume_usd = avg_hourly_volume * Decimal("24")

    if tvl_usd > 0:
        daily_fees_tvl_pct = avg_daily_fees_usd / tvl_usd
        daily_volume_tvl_pct = avg_daily_volume_usd / tvl_usd
        average_apr = (total_fees / tvl_usd) * (Decimal("365") / Decimal(timeframe_days)) * Decimal("100")
    else:
        daily_fees_tvl_pct = Decimal("0")
        daily_volume_tvl_pct = Decimal("0")
        average_apr = Decimal("0")

    return DiscoverPoolItem(
        pool_id=row.pool_id,
        pool_address=row.pool_address,
        pool_name=f"{row.token0_symbol} / {row.token1_symbol}",
        network=row.network_name,
        exchange=row.exchange_name,
        fee_tier=row.fee_tier,
        average_apr=average_apr,
        price_volatility=None,
        tvl_usd=tvl_usd,
        correlation=None,
        avg_daily_fees_usd=avg_daily_fees_usd,
        daily_fees_tvl_pct=daily_fees_tvl_pct,
        avg_daily_volume_usd=avg_daily_volume_usd,
        daily_volume_tvl_pct=daily_volume_tvl_pct,
    )
