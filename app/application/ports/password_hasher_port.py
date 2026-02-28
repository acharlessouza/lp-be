from __future__ import annotations

from typing import Protocol


class PasswordHasherPort(Protocol):
    def hash(self, plain_password: str) -> str:
        ...

    def verify(self, plain_password: str, password_hash: str) -> bool:
        ...
