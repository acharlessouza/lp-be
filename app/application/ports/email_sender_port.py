from __future__ import annotations

from typing import Protocol


class EmailSenderPort(Protocol):
    def send_password_reset_email(self, *, to_email: str, reset_link: str) -> None:
        ...
