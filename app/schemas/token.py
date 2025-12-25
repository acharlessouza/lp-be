from __future__ import annotations

from pydantic import BaseModel


class TokenResponse(BaseModel):
    address: str
    symbol: str
    decimals: int
