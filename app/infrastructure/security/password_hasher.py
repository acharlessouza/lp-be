from __future__ import annotations

from passlib.context import CryptContext

from app.application.ports.password_hasher_port import PasswordHasherPort


class PasswordHasher(PasswordHasherPort):
    def __init__(self):
        self._ctx = CryptContext(
            schemes=["argon2", "bcrypt"],
            deprecated="auto",
        )

    def hash(self, plain_password: str) -> str:
        return self._ctx.hash(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        try:
            return self._ctx.verify(plain_password, password_hash)
        except Exception:
            return False

    def verify_and_update(self, plain_password: str, password_hash: str) -> tuple[bool, str | None]:
        try:
            verified, replacement_hash = self._ctx.verify_and_update(plain_password, password_hash)
            return bool(verified), replacement_hash
        except Exception:
            return False, None
