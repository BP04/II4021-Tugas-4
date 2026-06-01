from __future__ import annotations

import secrets


def generate_key(length: int = 16) -> bytes:
    return secrets.token_bytes(length)


def encrypt():
    pass


def decrypt():
    pass
