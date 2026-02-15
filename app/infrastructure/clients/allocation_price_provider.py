from __future__ import annotations

from decimal import Decimal

from app.application.ports.token_price_port import TokenPricePort
from app.domain.exceptions import PriceLookupDomainError
from app.infrastructure.clients.pricing import PriceLookupError, PriceService


class PriceServiceAdapter(TokenPricePort):
    def __init__(self, price_service: PriceService):
        self._price_service = price_service

    def get_pair_prices(
        self,
        *,
        token0_address: str,
        token1_address: str,
        network: str,
    ) -> tuple[Decimal, Decimal]:
        try:
            return self._price_service.get_pair_prices(
                token0=token0_address,
                token1=token1_address,
                network=network,
            )
        except PriceLookupError as exc:
            raise PriceLookupDomainError(str(exc)) from exc
