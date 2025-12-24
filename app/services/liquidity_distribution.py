from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LiquidityBin:
    price_start: Decimal
    price_end: Decimal
    liquidity: Decimal
    ticks_count: int
    in_range: bool


@dataclass(frozen=True)
class LiquidityDistribution:
    range1: Decimal | None
    range2: Decimal | None
    range_ticks_count: int
    range_liquidity: Decimal
    bins: list[LiquidityBin]


class LiquidityDistributionService:
    def build(
        self,
        *,
        rows: list[tuple],
        bins: int,
        price_base: str,
        range1: Decimal | None,
        range2: Decimal | None,
    ) -> LiquidityDistribution:
        if price_base not in {"token0_per_token1", "token1_per_token0"}:
            raise ValueError("price_base must be token0_per_token1 or token1_per_token0.")

        points: list[tuple[Decimal, Decimal]] = []
        current_liquidity = Decimal("0")
        for tick_idx, price0, price1, liquidity_net in rows:
            if liquidity_net is None:
                continue
            current_liquidity += Decimal(str(liquidity_net))
            if current_liquidity <= 0:
                continue
            price_value = price0 if price_base == "token0_per_token1" else price1
            if price_value is None:
                continue
            price_dec = Decimal(str(price_value))
            if price_dec <= 0:
                continue
            points.append((price_dec, current_liquidity))

        if not points:
            raise ValueError("No tick snapshot data found.")

        points.sort(key=lambda item: item[0])
        min_price = points[0][0]
        max_price = points[-1][0]
        total_liquidity = sum(liquidity for _, liquidity in points)
        if total_liquidity <= 0:
            raise ValueError("Total liquidity is zero.")

        trim_count = int(len(points) * 0.02)
        if trim_count > 0 and len(points) - (trim_count * 2) >= 2:
            min_price = points[trim_count][0]
            max_price = points[-trim_count - 1][0]

        if range1 is not None and range2 is not None:
            range_min = min(range1, range2)
            range_max = max(range1, range2)
            if range_min < min_price:
                min_price = range_min
            if range_max > max_price:
                max_price = range_max

        if min_price == max_price:
            raise ValueError("Price range is empty.")

        bin_size = (max_price - min_price) / Decimal(bins)
        bin_rows = [Decimal("0") for _ in range(bins)]
        bin_counts = [0 for _ in range(bins)]

        for price, liquidity in points:
            if price < min_price or price > max_price:
                continue
            idx = int((price - min_price) / bin_size)
            if idx < 0:
                idx = 0
            if idx >= bins:
                idx = bins - 1
            bin_rows[idx] += liquidity
            bin_counts[idx] += 1

        range_min = None
        range_max = None
        if range1 is not None and range2 is not None:
            range_min = min(range1, range2)
            range_max = max(range1, range2)

        bins_out: list[LiquidityBin] = []
        range_liquidity = Decimal("0")
        range_ticks = 0
        for idx in range(bins):
            start = min_price + bin_size * Decimal(idx)
            end = start + bin_size
            mid = (start + end) / Decimal(2)
            in_range = False
            if range_min is not None and range_max is not None:
                in_range = range_min <= mid <= range_max
            liquidity = bin_rows[idx]
            ticks_count = bin_counts[idx]
            if in_range:
                range_liquidity += liquidity
                range_ticks += ticks_count
            bins_out.append(
                LiquidityBin(
                    price_start=start,
                    price_end=end,
                    liquidity=liquidity,
                    ticks_count=ticks_count,
                    in_range=in_range,
                )
            )

        return LiquidityDistribution(
            range1=range1,
            range2=range2,
            range_ticks_count=range_ticks,
            range_liquidity=range_liquidity,
            bins=bins_out,
        )
