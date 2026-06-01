from __future__ import annotations

from shared.models import VaultEntry, VaultPayload


class VaultManager:
    def __init__(self, payload: VaultPayload | None = None) -> None:
        self.payload = payload or VaultPayload(entries=[])
