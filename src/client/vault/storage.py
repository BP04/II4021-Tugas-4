import base64
import json
import tempfile
from pathlib import Path
from typing import Any

from client.crypto.kdf import kdf_params
from shared.config import client_data_dir
from shared.models import RecoverySharePreviewPaths, RecoveryShareVisualPaths


class ClientStorage:
    def __init__(self, base_dir: str | None = None) -> None:
        base_dir = base_dir or client_data_dir()
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def user_path(self, username: str) -> Path:
        return self.base_dir / f"{username}.json"

    def exists(self, username: str) -> bool:
        return self.user_path(username).exists()

    def save_user(
        self,
        username: str,
        encrypted_local_share: bytes,
        local_share_nonce: bytes,
        salt: bytes,
        backup_vault: bytes,
        backup_nonce: bytes,
    ) -> None:
        data = {
            "username": username,
            "kdf": kdf_params(),
            "salt": _b64e(salt),
            "encrypted_local_share": _b64e(encrypted_local_share),
            "local_share_nonce": _b64e(local_share_nonce),
            "backup_vault": _b64e(backup_vault),
            "backup_nonce": _b64e(backup_nonce),
        }
        self.user_path(username).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load_local_share_payload(self, username: str) -> dict[str, bytes]:
        data = self._load_raw_user(username)
        return {
            "salt": _b64d(data["salt"]),
            "encrypted_local_share": _b64d(data["encrypted_local_share"]),
            "local_share_nonce": _b64d(data["local_share_nonce"]),
        }

    def load_backup_payload(self, username: str) -> dict[str, bytes]:
        data = self._load_raw_user(username)
        return {
            "backup_vault": _b64d(data["backup_vault"]),
            "backup_nonce": _b64d(data["backup_nonce"]),
        }

    def update_backup(self, username: str, backup_vault: bytes, backup_nonce: bytes) -> None:
        data = json.loads(self.user_path(username).read_text(encoding="utf-8"))
        data["backup_vault"] = _b64e(backup_vault)
        data["backup_nonce"] = _b64e(backup_nonce)
        self.user_path(username).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save_recovery_preview(
        self,
        username: str,
        qr_code: bytes,
        overlay: bytes,
    ) -> RecoverySharePreviewPaths:
        target = Path(tempfile.mkdtemp(prefix=f"{username}_recovery_preview_"))
        qr_code_path = target / "recovery_qr.png"
        overlay_path = target / "overlay.png"
        qr_code_path.write_bytes(qr_code)
        overlay_path.write_bytes(overlay)
        return RecoverySharePreviewPaths(
            qr_code=str(qr_code_path),
            overlay=str(overlay_path),
        )

    def save_recovery_shares(
        self,
        share_one_path: str,
        share_two_path: str,
        share_one: bytes,
        share_two: bytes,
    ) -> RecoveryShareVisualPaths:
        first_path = self._resolve_share_output_path(share_one_path, "share 1")
        second_path = self._resolve_share_output_path(share_two_path, "share 2")
        if first_path == second_path:
            raise ValueError("share 1 and share 2 must use different output paths")
        try:
            first_path.write_bytes(share_one)
        except OSError as exc:
            raise ValueError(f"failed to save share 1 image to {first_path}: {exc.strerror or exc}") from exc
        try:
            second_path.write_bytes(share_two)
        except OSError as exc:
            try:
                first_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ValueError(f"failed to save share 2 image to {second_path}: {exc.strerror or exc}") from exc
        return RecoveryShareVisualPaths(
            share_one=str(first_path),
            share_two=str(second_path),
        )

    def _load_raw_user(self, username: str) -> dict[str, Any]:
        try:
            return json.loads(self.user_path(username).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError("local user data not found") from exc

    def _resolve_share_output_path(self, raw_path: str, label: str) -> Path:
        path = Path(raw_path.strip()).expanduser()
        if not raw_path.strip():
            raise ValueError(f"{label} output path is required")
        if not path.is_absolute():
            raise ValueError(f"{label} output path must be absolute: {raw_path}")
        parent = path.parent
        if not parent.exists():
            raise ValueError(f"{label} output directory not found: {parent}")
        if not parent.is_dir():
            raise ValueError(f"{label} output directory is not a folder: {parent}")
        if path.exists():
            raise ValueError(f"{label} output file already exists: {path}")
        return path


ClientStore = ClientStorage


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))