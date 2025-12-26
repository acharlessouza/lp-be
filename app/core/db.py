from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=4)
def get_engine(dsn: str):
    return create_engine(dsn, future=True, pool_pre_ping=True)


@lru_cache(maxsize=4)
def get_session_factory(dsn: str):
    engine = get_engine(dsn)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
