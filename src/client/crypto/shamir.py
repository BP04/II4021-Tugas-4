import base64
import json
import secrets
from dataclasses import dataclass
from typing import Any

PRIME = 257
SECRET_BYTES = 16


@dataclass(frozen=True, slots=True)
class Share:
    x: int
    y: bytes

    def to_text(self) -> str:
        payload = {"x": self.x, "y": base64.b64encode(self.y).decode("ascii")}
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @classmethod
    def from_text(cls, text: str) -> "Share":
        try:
            raw = base64.urlsafe_b64decode(text.encode("ascii"))
            payload = json.loads(raw.decode("utf-8"))
            x = int(payload["x"])
            y = base64.b64decode(str(payload["y"]).encode("ascii"))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid share format") from exc
        if x < 1 or len(y) != SECRET_BYTES * 2:
            raise ValueError("invalid share content")
        return cls(x=x, y=y)

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": base64.b64encode(self.y).decode("ascii")}


def share_to_dict(share: Share) -> dict[str, Any]:
    return share.to_dict()


def share_from_dict(data: dict[str, Any]) -> Share:
    try:
        x = int(data["x"])
        y = base64.b64decode(str(data["y"]).encode("ascii"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid share format") from exc
    return Share(x=x, y=y)


def split_secret(secret: bytes) -> tuple[Share, Share, Share]:
    if len(secret) != SECRET_BYTES:
        raise ValueError("secret must be 16 bytes for AES-128")
    slopes = [secrets.randbelow(PRIME) for _ in secret]
    return tuple(_make_share(x, secret, slopes) for x in (1, 2, 3))


def combine_shares(shares: list[Share] | tuple[Share, Share]) -> bytes:
    if len(shares) < 2:
        raise ValueError("at least two shares are required")
    first, second = shares[0], shares[1]
    if first.x == second.x:
        raise ValueError("shares must use distinct x coordinates")
    secret = bytearray()
    y1 = _decode_y(first.y)
    y2 = _decode_y(second.y)
    for a, b in zip(y1, y2, strict=True):
        value = _interpolate_at_zero(first.x, a, second.x, b)
        if value > 255:
            raise ValueError("invalid reconstructed secret")
        secret.append(value)
    return bytes(secret)


def join_shares(shares: list[tuple[int, bytes]] | list[Share]) -> bytes:
    normalized = [share if isinstance(share, Share) else Share(x=share[0], y=share[1]) for share in shares]
    return combine_shares(normalized)


def _make_share(x: int, secret: bytes, slopes: list[int]) -> Share:
    values = [(byte + slope * x) % PRIME for byte, slope in zip(secret, slopes, strict=True)]
    return Share(x=x, y=_encode_y(values))


def _encode_y(values: list[int]) -> bytes:
    encoded = bytearray()
    for value in values:
        encoded.extend(value.to_bytes(2, "big"))
    return bytes(encoded)


def _decode_y(data: bytes) -> list[int]:
    if len(data) != SECRET_BYTES * 2:
        raise ValueError("invalid share length")
    values = [int.from_bytes(data[index : index + 2], "big") for index in range(0, len(data), 2)]
    if any(value >= PRIME for value in values):
        raise ValueError("invalid share value")
    return values


def _interpolate_at_zero(x1: int, y1: int, x2: int, y2: int) -> int:
    numerator = (x2 * y1 - x1 * y2) % PRIME
    denominator = (x2 - x1) % PRIME
    return numerator * pow(denominator, -1, PRIME) % PRIME