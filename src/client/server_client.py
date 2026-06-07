import base64
import json
import urllib.error
import urllib.request
from typing import Any

from shared.config import server_url


class ServerClient:
    def __init__(self, base_url: str | None = None) -> None:
        base_url = base_url or server_url()
        self.base_url = base_url.rstrip("/")

    def create_user(self, username: str, server_share: str, vault: bytes, nonce: bytes) -> None:
        self._request(
            "POST",
            "/users",
            {
                "username": username,
                "server_share": server_share,
                **_encoded_vault_payload(vault, nonce),
            },
        )

    def load_server_share(self, username: str) -> str:
        data = self._request("GET", f"/users/{username}/share")
        return str(data["server_share"])

    def load_vault_payload(self, username: str) -> dict[str, bytes]:
        data = self._request("GET", f"/users/{username}/vault")
        return {
            "vault": _b64d(str(data["vault"])),
            "nonce": _b64d(str(data["nonce"])),
        }

    def update_vault(self, username: str, vault: bytes, nonce: bytes) -> None:
        self._request(
            "PUT",
            f"/users/{username}/vault",
            _encoded_vault_payload(vault, nonce),
        )

    def is_available(self) -> bool:
        try:
            self._request("GET", "/health")
        except ValueError:
            return False
        return True

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read().decode("utf-8"))["detail"]
            except (json.JSONDecodeError, KeyError, TypeError):
                message = exc.reason
            raise ValueError(str(message)) from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"server is not reachable on {self.base_url}") from exc
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))


def _encoded_vault_payload(vault: bytes, nonce: bytes) -> dict[str, str]:
    return {
        "vault_blob": _b64e(vault),
        "vault_nonce": _b64e(nonce),
    }