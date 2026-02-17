from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.simulate_apr import SimulateAprHourly
from app.domain.services.liquidity import LiquidityCurve, active_liquidity_at_tick


@dataclass(frozen=True)
class AprSimulationDiagnostics:
    hours_total: int
    hours_in_range: int
    percent_time_in_range: Decimal
    avg_share_in_range: Decimal
    warnings: list[str]


@dataclass(frozen=True)
class AprSimulationResult:
    estimated_fees_24h_usd: Decimal
    fees_period_usd: Decimal
    monthly_usd: Decimal
    yearly_usd: Decimal
    fee_apr: Decimal
    diagnostics: AprSimulationDiagnostics


def simulate_fee_apr(
    *,
    hourly_fees: list[SimulateAprHourly],
    hourly_ticks: dict[datetime, int],
    hourly_liquidity: dict[datetime, Decimal] | None,
    liquidity_curve: LiquidityCurve,
    l_user: Decimal,
    tick_lower: int,
    tick_upper: int,
    full_range: bool,
    mode: str,
    fallback_tick: int,
    latest_pool_liquidity: Decimal | None,
    horizon_hours: int,
    annualization_days: Decimal,
    deposit_usd: Decimal | None,
    warnings: list[str] | None = None,
) -> AprSimulationResult:
    current_warnings = list(warnings or [])
    if not hourly_fees:
        return AprSimulationResult(
            estimated_fees_24h_usd=Decimal("0"),
            fees_period_usd=Decimal("0"),
            monthly_usd=Decimal("0"),
            yearly_usd=Decimal("0"),
            fee_apr=Decimal("0"),
            diagnostics=AprSimulationDiagnostics(
                hours_total=0,
                hours_in_range=0,
                percent_time_in_range=Decimal("0"),
                avg_share_in_range=Decimal("0"),
                warnings=current_warnings,
            ),
        )

    rows = sorted(hourly_fees, key=lambda row: row.hour_ts)
    fees_user_hourly: list[Decimal] = []
    shares_in_range: list[Decimal] = []
    hours_in_range = 0
    missing_tick_warning_added = False
    missing_liquidity_curve_warning_added = False
    missing_liquidity_latest_warning_added = False
    missing_liquidity_zero_warning_added = False
    liquidity_by_hour = hourly_liquidity or {}

    for row in rows:
        tick_h = fallback_tick
        if mode == "B":
            tick_candidate = hourly_ticks.get(row.hour_ts)
            if tick_candidate is None:
                if not missing_tick_warning_added:
                    current_warnings.append(
                        "Missing snapshot ticks for some hours; mode B fell back to current tick."
                    )
                    missing_tick_warning_added = True
            else:
                tick_h = tick_candidate

        if full_range or (tick_lower <= tick_h <= tick_upper):
            hours_in_range += 1
            snapshot_liquidity = liquidity_by_hour.get(row.hour_ts)
            if snapshot_liquidity is not None and snapshot_liquidity > 0:
                l_pool_active = snapshot_liquidity
            else:
                l_pool_active = active_liquidity_at_tick(curve=liquidity_curve, tick=tick_h)
                if l_pool_active <= 0 and latest_pool_liquidity is not None and latest_pool_liquidity > 0:
                    l_pool_active = latest_pool_liquidity
                    if not missing_liquidity_latest_warning_added:
                        current_warnings.append(
                            "Missing snapshot liquidity for some hours; fell back to latest pool liquidity."
                        )
                        missing_liquidity_latest_warning_added = True
                elif l_pool_active > 0:
                    if not missing_liquidity_curve_warning_added:
                        current_warnings.append(
                            "Missing snapshot liquidity for some hours; fell back to initialized-ticks active liquidity."
                        )
                        missing_liquidity_curve_warning_added = True
                elif not missing_liquidity_zero_warning_added:
                    current_warnings.append(
                        "Missing snapshot liquidity for some hours and no fallback liquidity available."
                    )
                    missing_liquidity_zero_warning_added = True
            denom = l_pool_active + l_user
            share = (l_user / denom) if denom > 0 and l_user > 0 else Decimal("0")
            shares_in_range.append(share)
            fees_user_hourly.append(row.fees_usd * share)
        else:
            fees_user_hourly.append(Decimal("0"))

    hours_total = len(rows)
    percent_time = (
        (Decimal(hours_in_range) / Decimal(hours_total)) * Decimal("100")
        if hours_total > 0
        else Decimal("0")
    )
    avg_share = (
        sum(shares_in_range, Decimal("0")) / Decimal(len(shares_in_range))
        if shares_in_range
        else Decimal("0")
    )

    # Raw last-24h fees (useful reference), but the public "estimated_fees_24h_usd"
    # is derived from the selected horizon to make horizon affect the output.
    hours_24h = min(24, len(fees_user_hourly))
    fees_last_24h = sum(fees_user_hourly[-hours_24h:], Decimal("0"))

    period_hours = min(horizon_hours, len(fees_user_hourly))
    if period_hours < horizon_hours:
        current_warnings.append("Insufficient hourly data for selected horizon.")
    fees_period = sum(fees_user_hourly[-period_hours:], Decimal("0"))

    # Estimated 24h fees based on the selected horizon (average over period scaled to 24h).
    # This ensures horizon=1d,2d,... changes the estimate when the underlying period average differs.
    effective_days = Decimal(period_hours) / Decimal("24")
    estimated_fees_24h = (fees_period / effective_days) if effective_days > 0 else Decimal("0")

    # monthly/yearly consistent with the 24h estimate.
    monthly = estimated_fees_24h * Decimal("30")
    yearly = estimated_fees_24h * Decimal("365")

    fee_apr = Decimal("0")
    if deposit_usd is not None and deposit_usd > 0:
        fee_apr = yearly / deposit_usd
    else:
        current_warnings.append("deposit_usd unavailable; fee_apr returned as 0.")

    return AprSimulationResult(
        estimated_fees_24h_usd=estimated_fees_24h,
        fees_period_usd=fees_period,
        monthly_usd=monthly,
        yearly_usd=yearly,
        fee_apr=fee_apr,
        diagnostics=AprSimulationDiagnostics(
            hours_total=hours_total,
            hours_in_range=hours_in_range,
            percent_time_in_range=percent_time,
            avg_share_in_range=avg_share,
            warnings=current_warnings,
        ),
    )
