from __future__ import annotations

from decimal import Decimal

from app.application.dto.pool_volume_history import (
    GetPoolVolumeHistoryOutput,
    GetPoolVolumeHistoryInput,
    PoolVolumeHistoryPointOutput,
    PoolVolumeHistorySummaryOutput,
)
from app.application.ports.pool_volume_history_port import PoolVolumeHistoryPort
from app.domain.exceptions import PoolVolumeHistoryInputError
from app.domain.services.pool_summary import calculate_daily_tvl_pct


class GetPoolVolumeHistoryUseCase:
    def __init__(self, *, pool_volume_history_port: PoolVolumeHistoryPort):
        self._pool_volume_history_port = pool_volume_history_port

    def execute(self, command: GetPoolVolumeHistoryInput) -> GetPoolVolumeHistoryOutput:
        if not command.pool_address or not command.pool_address.lower().startswith("0x"):
            raise PoolVolumeHistoryInputError("pool_address must start with 0x.")
        if command.days < 1 or command.days > 365:
            raise PoolVolumeHistoryInputError("days must be between 1 and 365.")
        if command.chain_id is not None and command.chain_id <= 0:
            raise PoolVolumeHistoryInputError("chain_id must be a positive integer when provided.")
        if command.dex_id is not None and command.dex_id <= 0:
            raise PoolVolumeHistoryInputError("dex_id must be a positive integer when provided.")

        rows = self._pool_volume_history_port.list_daily_volume_history(
            pool_address=command.pool_address.lower(),
            days=command.days,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )
        ordered = sorted(rows, key=lambda row: row.time)
        points = [
            PoolVolumeHistoryPointOutput(
                time=row.time,
                value=row.value,
                fees_usd=row.fees_usd,
            )
            for row in ordered
        ]
        avg_daily_fees_usd: Decimal | None = None
        avg_daily_volume_usd: Decimal | None = None
        if points:
            count = Decimal(len(points))
            avg_daily_fees_usd = sum((row.fees_usd for row in points), Decimal("0")) / count
            avg_daily_volume_usd = sum((row.value for row in points), Decimal("0")) / count

        base = self._pool_volume_history_port.get_summary_base(
            pool_address=command.pool_address.lower(),
            days=command.days,
            chain_id=command.chain_id,
            dex_id=command.dex_id,
        )

        daily_fees_tvl_pct = calculate_daily_tvl_pct(
            avg_daily_usd=avg_daily_fees_usd,
            tvl_usd=base.tvl_usd,
        )
        daily_volume_tvl_pct = calculate_daily_tvl_pct(
            avg_daily_usd=avg_daily_volume_usd,
            tvl_usd=base.tvl_usd,
        )

        price_volatility_pct: Decimal | None = None
        correlation: Decimal | None = None
        geometric_mean_price: Decimal | None = None

        summary = PoolVolumeHistorySummaryOutput(
            tvl_usd=base.tvl_usd,
            avg_daily_fees_usd=avg_daily_fees_usd,
            daily_fees_tvl_pct=daily_fees_tvl_pct,
            avg_daily_volume_usd=avg_daily_volume_usd,
            daily_volume_tvl_pct=daily_volume_tvl_pct,
            price_volatility_pct=price_volatility_pct,
            correlation=correlation,
            geometric_mean_price=geometric_mean_price,
        )
        return GetPoolVolumeHistoryOutput(volume_history=points, summary=summary)
