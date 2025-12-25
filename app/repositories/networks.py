from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text


@dataclass(frozen=True)
class NetworkRow:
    id: int
    name: str


class NetworkRepository:
    def __init__(self, engine):
        self._engine = engine

    def list_by_exchange(self, exchange_id: int) -> list[NetworkRow]:
        sql = """
            SELECT DISTINCT
                n.id,
                n.name
            FROM networks n
            JOIN pools p ON p.network_id = n.id
            WHERE p.exchange_id = :exchange_id
            ORDER BY n.name
        """
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), {"exchange_id": exchange_id}).mappings().all()

        return [NetworkRow(id=row["id"], name=row["name"]) for row in rows]
