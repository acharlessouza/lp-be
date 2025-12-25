from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text


@dataclass(frozen=True)
class ExchangeRow:
    id: int
    name: str


class ExchangeRepository:
    def __init__(self, engine):
        self._engine = engine

    def list_all(self) -> list[ExchangeRow]:
        sql = """
            SELECT
                id,
                name
            FROM exchanges
            ORDER BY name
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql)).mappings().all()

        return [ExchangeRow(id=row["id"], name=row["name"]) for row in rows]
