from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Exchange:
    id: int
    name: str


@dataclass(frozen=True)
class Network:
    id: int
    name: str


@dataclass(frozen=True)
class Token:
    address: str
    symbol: str
    decimals: int


@dataclass(frozen=True)
class PoolSummary:
    pool_address: str
    fee_tier: int


@dataclass(frozen=True)
class PoolDetail:
    id: str
    fee_tier: int
    token0_address: str
    token0_symbol: str
    token0_decimals: int
    token1_address: str
    token1_symbol: str
    token1_decimals: int
