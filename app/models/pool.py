from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey

from ..core.db import Base


class Pool(Base):
    __tablename__ = "pools"

    id = Column(Integer, primary_key=True)
    network_id = Column(Integer, ForeignKey("networks.id"), nullable=False)
    pool_address = Column(String(64), nullable=False)
    fee_tier = Column(Integer, nullable=False)

    token0_address = Column(String(64), nullable=False)
    token0_symbol = Column(String(32), nullable=False)
    token0_decimals = Column(Integer, nullable=False)

    token1_address = Column(String(64), nullable=False)
    token1_symbol = Column(String(32), nullable=False)
    token1_decimals = Column(Integer, nullable=False)
