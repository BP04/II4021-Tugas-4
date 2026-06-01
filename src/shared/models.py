from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecoveryShare:
    x: int
    y: str

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RecoveryShare":
        return RecoveryShare(x=int(data["x"]), y=str(data["y"]))


@dataclass
class VaultEntry:
    service: str
    username: str
    password: str
    note: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "service": self.service,
            "username": self.username,
            "password": self.password,
            "note": self.note,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VaultEntry":
        return VaultEntry(
            service=str(data["service"]),
            username=str(data["username"]),
            password=str(data["password"]),
            note=str(data.get("note", "")),
        )


@dataclass
class VaultPayload:
    entries: list[VaultEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [entry.to_dict() for entry in self.entries]}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VaultPayload":
        entries = [VaultEntry.from_dict(raw) for raw in data.get("entries", [])]
        return VaultPayload(entries=entries)
