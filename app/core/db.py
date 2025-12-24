from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_engine(dsn: str):
    return create_engine(dsn, future=True)


def get_session_factory(dsn: str):
    engine = get_engine(dsn)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
