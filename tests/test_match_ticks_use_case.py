from __future__ import annotations

from decimal import Decimal

import pytest

from app.application.dto.match_ticks import MatchTicksInput
from app.application.use_cases.match_ticks import MatchTicksUseCase
from app.domain.entities.match_ticks import MatchTicksLatestPrices, MatchTicksPoolConfig
from app.domain.exceptions import MatchTicksInputError


class FakeMatchTicksPort:
    def get_pool_config(self, *, pool_id: int) -> MatchTicksPoolConfig | None:
        _ = pool_id
        return MatchTicksPoolConfig(fee_tier=3000)

    def get_latest_prices(self, *, pool_id: int) -> MatchTicksLatestPrices | None:
        _ = pool_id
        return MatchTicksLatestPrices(token0_price=None, token1_price=Decimal("2"))


def test_swapped_pair_matches_in_canonical_and_returns_ui_prices():
    use_case = MatchTicksUseCase(match_ticks_port=FakeMatchTicksPort())

    canonical = use_case.execute(
        MatchTicksInput(
            pool_id=1,
            min_price=Decimal("1.5"),
            max_price=Decimal("2.5"),
            swapped_pair=False,
        )
    )
    swapped = use_case.execute(
        MatchTicksInput(
            pool_id=1,
            min_price=Decimal("0.4"),
            max_price=Decimal("0.6666666666666667"),
            swapped_pair=True,
        )
    )

    assert swapped.min_price_matched == pytest.approx(1 / canonical.max_price_matched)
    assert swapped.max_price_matched == pytest.approx(1 / canonical.min_price_matched)
    assert swapped.current_price_matched == pytest.approx(1 / canonical.current_price_matched)


def test_swapped_pair_rejects_non_positive_prices():
    use_case = MatchTicksUseCase(match_ticks_port=FakeMatchTicksPort())

    with pytest.raises(MatchTicksInputError):
        use_case.execute(
            MatchTicksInput(
                pool_id=1,
                min_price=Decimal("0"),
                max_price=Decimal("1"),
                swapped_pair=True,
            )
        )
