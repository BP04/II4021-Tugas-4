import os
from pathlib import Path

from client.crypto import (
    Share,
    combine_shares,
    create_recovery_share_visuals,
    decrypt_bytes,
    derive_key,
    encrypt_bytes,
    new_salt,
    recover_recovery_share_from_visuals,
    split_secret,
)
from client.server_client import ServerClient
from client.vault.codec import decode_entries, encode_entries
from client.vault.storage import ClientStorage
from shared.config import client_data_dir
from shared.models import CreatedVault, OpenVault, RecoveryShareVisualPaths, VaultEntry

MASTER_KEY_BYTES = 16
READ_ONLY_VAULT_MESSAGE = "backup mode is read-only"


class VaultManager:
    def __init__(self, data_dir: Path | None = None) -> None:
        storage_dir = Path(client_data_dir()) if data_dir is None else _resolve_client_storage_dir(Path(data_dir))
        self.client_store = ClientStorage(str(storage_dir))
        self.server = ServerClient()

    def create_vault(self, username: str, master_password: str) -> CreatedVault:
        if self.client_store.exists(username):
            raise ValueError("local user already exists")
        master_key = os.urandom(MASTER_KEY_BYTES)
        empty_vault = encode_entries([])
        (encrypted_vault, vault_nonce), (backup_vault, backup_nonce) = _encrypt_copies(master_key, empty_vault)
        local_share, server_share, recovery_share = split_secret(master_key)
        visual_assets = create_recovery_share_visuals(recovery_share.to_text())
        salt = new_salt()
        password_key = derive_key(master_password, salt)
        encrypted_local_share, local_nonce = encrypt_bytes(password_key, local_share.to_text().encode("utf-8"))
        self.server.create_user(username, server_share.to_text(), encrypted_vault, vault_nonce)
        self.client_store.save_user(
            username,
            encrypted_local_share,
            local_nonce,
            salt,
            backup_vault,
            backup_nonce,
        )
        preview_paths = self.client_store.save_recovery_preview(
            username,
            visual_assets.qr_code,
            visual_assets.overlay,
        )
        return CreatedVault(
            recovery_share=recovery_share.to_text(),
            share_one_png=visual_assets.share_one,
            share_two_png=visual_assets.share_two,
            preview_paths=preview_paths,
        )

    def save_recovery_shares(
        self,
        created_vault: CreatedVault,
        share_one_path: str,
        share_two_path: str,
    ) -> RecoveryShareVisualPaths:
        return self.client_store.save_recovery_shares(
            share_one_path,
            share_two_path,
            created_vault.share_one_png,
            created_vault.share_two_png,
        )

    def username_exists(self, username: str) -> bool:
        if self.client_store.exists(username):
            return True
        try:
            self.server.load_server_share(username)
        except ValueError as exc:
            if str(exc) == "server user data not found":
                return False
            raise
        return True

    def save_normal(self, vault: OpenVault) -> None:
        if vault.readonly:
            raise ValueError(READ_ONLY_VAULT_MESSAGE)
        plaintext = encode_entries(vault.entries)
        (encrypted_vault, vault_nonce), (backup_vault, backup_nonce) = _encrypt_copies(vault.master_key, plaintext)
        self.server.update_vault(vault.username, encrypted_vault, vault_nonce)
        self.client_store.update_backup(vault.username, backup_vault, backup_nonce)

    def add_entry(self, vault: OpenVault, entry: VaultEntry) -> None:
        self._require_writable(vault)
        vault.entries.append(entry)
        self.save_normal(vault)

    def update_entry(self, vault: OpenVault, index: int, entry: VaultEntry) -> None:
        self._require_writable(vault)
        vault.entries[index] = entry
        self.save_normal(vault)

    def delete_entry(self, vault: OpenVault, index: int) -> None:
        self._require_writable(vault)
        del vault.entries[index]
        self.save_normal(vault)

    def unlock_local_share(self, username: str, master_password: str) -> Share:
        client_data = self.client_store.load_local_share_payload(username)
        password_key = derive_key(master_password, client_data["salt"])
        plaintext = decrypt_bytes(
            password_key,
            client_data["encrypted_local_share"],
            client_data["local_share_nonce"],
        )
        return Share.from_text(plaintext.decode("utf-8"))

    def open_normal_with_local_share(self, username: str, local_share: Share) -> OpenVault:
        server_share = Share.from_text(self.server.load_server_share(username))
        vault_data = self.server.load_vault_payload(username)
        master_key = combine_shares([local_share, server_share])
        plaintext = decrypt_bytes(master_key, vault_data["vault"], vault_data["nonce"])
        return OpenVault(username=username, entries=decode_entries(plaintext), master_key=master_key, mode="normal")

    def open_backup_with_local_share(self, username: str, local_share: Share, recovery_share_text: str) -> OpenVault:
        recovery_share = Share.from_text(recovery_share_text.strip())
        client_data = self.client_store.load_backup_payload(username)
        master_key = combine_shares([local_share, recovery_share])
        plaintext = decrypt_bytes(master_key, client_data["backup_vault"], client_data["backup_nonce"])
        return OpenVault(username=username, entries=decode_entries(plaintext), master_key=master_key, mode="backup")

    def open_backup_with_visual_shares(
        self,
        username: str,
        local_share: Share,
        share_one_path: str,
        share_two_path: str,
    ) -> OpenVault:
        recovery_share_text = recover_recovery_share_from_visuals(share_one_path, share_two_path)
        return self.open_backup_with_local_share(username, local_share, recovery_share_text)

    def _require_writable(self, vault: OpenVault) -> None:
        if vault.readonly:
            raise ValueError(READ_ONLY_VAULT_MESSAGE)


VaultService = VaultManager


def _encrypt_copies(key: bytes, plaintext: bytes) -> tuple[tuple[bytes, bytes], tuple[bytes, bytes]]:
    return encrypt_bytes(key, plaintext), encrypt_bytes(key, plaintext)


def _resolve_client_storage_dir(data_dir: Path) -> Path:
    if data_dir.name == "client":
        return data_dir
    return data_dir / "client"