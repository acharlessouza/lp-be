from __future__ import annotations

from typing import Protocol
from typing import Tuple


class PasswordHasherPort(Protocol):
    def hash(self, plain_password: str) -> str:
        ...

    def verify(self, plain_password: str, password_hash: str) -> bool:
        ...

    def verify_and_update(self, plain_password: str, password_hash: str) -> Tuple[bool, str | None]:
        ...
