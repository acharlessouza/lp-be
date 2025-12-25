from __future__ import annotations

from pydantic import BaseModel


class NetworkResponse(BaseModel):
    id: int
    name: str
