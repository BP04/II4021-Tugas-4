from __future__ import annotations

import secrets


def generate_salt(length: int = 16) -> bytes:
    return secrets.token_bytes(length)


def derive_key():
    pass
