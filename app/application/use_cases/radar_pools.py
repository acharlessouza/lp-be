from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.application.dto.radar_pools import (
    RadarPoolOutputItem,
    RadarPoolsInput,
    RadarPoolsOutput,
)
from app.application.ports.radar_pools_port import RadarPoolsPort
from app.domain.exceptions import RadarPoolsInputError
from app.domain.services.radar_pools import build_radar_item


ORDER_FIELDS = {
    "pool_id": int,
    "pool_address": str,
    "pool_name": str,
    "network": str,
    "exchange": str,
    "dex_id": int,
    "chain_id": int,
    "token0_address": str,
    "token1_address": str,
    "token0_symbol": str,
    "token1_symbol": str,
    "token0_icon_url": str,
    "token1_icon_url": str,
    "fee_tier": int,
    "average_apr": Decimal,
    "price_volatility": Decimal,
    "tvl_usd": Decimal,
    "correlation": Decimal,
    "avg_daily_fees_usd": Decimal,
    "daily_fees_tvl_pct": Decimal,
    "avg_daily_volume_usd": Decimal,
    "daily_volume_tvl_pct": Decimal,
}


class RadarPoolsUseCase:
    def __init__(self, *, radar_pools_port: RadarPoolsPort):
        self._radar_pools_port = radar_pools_port

    def execute(self, command: RadarPoolsInput) -> RadarPoolsOutput:
        if command.timeframe_days < 1 or command.timeframe_days > 365:
            raise RadarPoolsInputError("timeframe_days must be between 1 and 365.")
        if command.page < 1:
            raise RadarPoolsInputError("page must be >= 1.")
        if command.page_size < 1 or command.page_size > 100:
            raise RadarPoolsInputError("page_size must be between 1 and 100.")
        if command.order_dir not in {"asc", "desc"}:
            raise RadarPoolsInputError("order_dir must be asc or desc.")
        if command.order_by not in ORDER_FIELDS:
            raise RadarPoolsInputError("order_by is not supported.")

        start_dt = datetime.utcnow() - timedelta(days=command.timeframe_days)
        rows = self._radar_pools_port.list_pools(
            start_dt=start_dt,
            network_id=command.network_id,
            exchange_id=command.exchange_id,
            token_symbol=command.token_symbol.upper() if command.token_symbol else None,
        )

        items = [
            build_radar_item(row=row, timeframe_days=command.timeframe_days)
            for row in rows
        ]

        def order_value(item: RadarPoolOutputItem | object):
            value = getattr(item, command.order_by)
            value_type = ORDER_FIELDS[command.order_by]
            if value is None:
                if value_type is str:
                    return ""
                if value_type is int:
                    return 0
                return Decimal("0")
            return value

        reverse = command.order_dir == "desc"
        sorted_items = sorted(items, key=order_value, reverse=reverse)
        total = len(sorted_items)
        offset = (command.page - 1) * command.page_size
        page_items = sorted_items[offset : offset + command.page_size]

        return RadarPoolsOutput(
            page=command.page,
            page_size=command.page_size,
            total=total,
            data=[
                RadarPoolOutputItem(
                    pool_id=row.pool_id,
                    pool_address=row.pool_address,
                    pool_name=row.pool_name,
                    network=row.network,
                    exchange=row.exchange,
                    dex_id=row.dex_id,
                    chain_id=row.chain_id,
                    token0_address=row.token0_address,
                    token1_address=row.token1_address,
                    token0_symbol=row.token0_symbol,
                    token1_symbol=row.token1_symbol,
                    token0_icon_url=row.token0_icon_url,
                    token1_icon_url=row.token1_icon_url,
                    fee_tier=row.fee_tier,
                    average_apr=row.average_apr,
                    price_volatility=row.price_volatility,
                    tvl_usd=row.tvl_usd,
                    correlation=row.correlation,
                    avg_daily_fees_usd=row.avg_daily_fees_usd,
                    daily_fees_tvl_pct=row.daily_fees_tvl_pct,
                    avg_daily_volume_usd=row.avg_daily_volume_usd,
                    daily_volume_tvl_pct=row.daily_volume_tvl_pct,
                )
                for row in page_items
            ],
        )
