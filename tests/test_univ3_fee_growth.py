from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.services.univ3_fee_growth import fee_growth_inside, fees_from_delta_inside, parse_uint256


class TestUniv3FeeGrowth:
    def test_fee_growth_inside_when_tick_is_inside_range(self):
        inside = fee_growth_inside(
            fee_growth_global=1000,
            fee_growth_outside_lower=100,
            fee_growth_outside_upper=200,
            tick_current=0,
            tick_lower=-10,
            tick_upper=10,
        )
        assert inside == 700

    def test_fee_growth_inside_when_tick_is_below_range(self):
        inside = fee_growth_inside(
            fee_growth_global=1000,
            fee_growth_outside_lower=300,
            fee_growth_outside_upper=100,
            tick_current=-20,
            tick_lower=-10,
            tick_upper=10,
        )
        assert inside == 200

    def test_fee_growth_inside_when_tick_is_above_range(self):
        inside = fee_growth_inside(
            fee_growth_global=1000,
            fee_growth_outside_lower=300,
            fee_growth_outside_upper=600,
            tick_current=20,
            tick_lower=-10,
            tick_upper=10,
        )
        assert inside == 300

    def test_parse_uint256_accepts_int_and_string(self):
        assert parse_uint256(123) == 123
        assert parse_uint256("456") == 456
        assert parse_uint256(Decimal("789")) == 789

    def test_fees_from_delta_inside_uses_q128(self):
        result = fees_from_delta_inside(delta_inside=2**128, user_liquidity=Decimal("3"))
        assert result == Decimal("3")

    def test_parse_uint256_rejects_invalid_values(self):
        with pytest.raises(ValueError):
            parse_uint256(None)
        with pytest.raises(ValueError):
            parse_uint256("")
        with pytest.raises(ValueError):
            parse_uint256(-1)
