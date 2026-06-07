from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RecoveryShare:
    x: int
    y: str

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "RecoveryShare":
        return RecoveryShare(x=int(data["x"]), y=str(data["y"]))


@dataclass(slots=True)
class VaultEntry:
    service: str
    username: str
    password: str
    notes: str = ""

    @property
    def note(self) -> str:
        return self.notes

    def to_dict(self) -> dict[str, str]:
        return {
            "service": self.service,
            "username": self.username,
            "password": self.password,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VaultEntry":
        return VaultEntry(
            service=str(data["service"]),
            username=str(data["username"]),
            password=str(data["password"]),
            notes=str(data.get("notes", data.get("note", ""))),
        )


@dataclass(slots=True)
class RecoveryShareVisualPaths:
    share_one: str
    share_two: str


@dataclass(slots=True)
class RecoverySharePreviewPaths:
    qr_code: str
    overlay: str


@dataclass(slots=True)
class CreatedVault:
    recovery_share: str
    share_one_png: bytes
    share_two_png: bytes
    preview_paths: RecoverySharePreviewPaths


@dataclass(slots=True)
class OpenVault:
    username: str
    entries: list[VaultEntry]
    master_key: bytes
    mode: str

    @property
    def readonly(self) -> bool:
        return self.mode == "backup"


@dataclass(slots=True)
class VaultPayload:
    entries: list[VaultEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [entry.to_dict() for entry in self.entries]}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "VaultPayload":
        entries = [VaultEntry.from_dict(raw) for raw in data.get("entries", [])]
        return VaultPayload(entries=entries)