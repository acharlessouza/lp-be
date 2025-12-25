from __future__ import annotations

from pydantic import BaseModel


class ExchangeResponse(BaseModel):
    id: int
    name: str
