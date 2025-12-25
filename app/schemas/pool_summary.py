from __future__ import annotations

from pydantic import BaseModel


class PoolSummaryResponse(BaseModel):
    pool_address: str
    fee_tier: int
