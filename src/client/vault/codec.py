import json
from dataclasses import asdict

from shared.models import VaultEntry


def encode_entries(entries: list[VaultEntry]) -> bytes:
    payload = {"entries": [asdict(entry) for entry in entries]}
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def decode_entries(data: bytes) -> list[VaultEntry]:
    payload = json.loads(data.decode("utf-8"))
    return [VaultEntry.from_dict(entry) for entry in payload.get("entries", [])]