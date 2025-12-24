from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric

from ..core.db import Base


class TickSnapshot(Base):
    __tablename__ = "tick_snapshots"

    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pools.id"), nullable=False)
    date = Column(Date, nullable=False)
    tick_idx = Column(Integer, nullable=False)

    liquidity_gross = Column(Numeric(78, 0))
    price0 = Column(Numeric(78, 18))
    price1 = Column(Numeric(78, 18))
