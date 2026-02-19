from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.auth import require_jwt
from app.api.deps import get_simulate_apr_v2_use_case
from app.application.dto.simulate_apr_v2 import SimulateAprV2MetaOutput, SimulateAprV2Output
from app.main import app


class FakeSimulateAprV2UseCase:
    def execute(self, _command):
        return SimulateAprV2Output(
            estimated_fees_period_usd=Decimal("1.23"),
            estimated_fees_24h_usd=Decimal("1.23"),
            monthly_usd=Decimal("37.45"),
            yearly_usd=Decimal("449.40"),
            fee_apr=Decimal("0.44"),
            meta=SimulateAprV2MetaOutput(
                block_a_number=10,
                block_b_number=20,
                ts_a=1000,
                ts_b=2000,
                seconds_delta=1000,
                used_price=Decimal("2"),
                warnings=["warn"],
            ),
        )


def test_router_v2_returns_response_with_meta():
    app.dependency_overrides[require_jwt] = lambda: "token"
    app.dependency_overrides[get_simulate_apr_v2_use_case] = lambda: FakeSimulateAprV2UseCase()

    client = TestClient(app)
    response = client.post(
        "/v2/simulate/apr",
        json={
            "pool_address": "0xpool",
            "chain_id": 1,
            "dex_id": 2,
            "deposit_usd": "1000",
            "amount_token0": "1",
            "amount_token1": "1",
            "full_range": False,
            "tick_lower": -10,
            "tick_upper": 10,
            "min_price": None,
            "max_price": None,
            "horizon": "24h",
            "lookback_days": 1,
            "calculation_method": "current",
            "custom_calculation_price": None,
            "apr_method": "exact",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimated_fees_period_usd"] == "1.23"
    assert payload["meta"]["block_a_number"] == 10
    assert payload["meta"]["used_price"] == "2"

    app.dependency_overrides.clear()
