from __future__ import annotations

from passlib.context import CryptContext

from app.application.ports.password_hasher_port import PasswordHasherPort


class BcryptPasswordHasher(PasswordHasherPort):
    def __init__(self):
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, plain_password: str) -> str:
        return self._ctx.hash(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return self._ctx.verify(plain_password, password_hash)
