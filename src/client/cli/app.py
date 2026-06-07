from typing import Callable

from client.app_state import app_state
from client.server_state import server_state
from client.vault import VaultService
from shared.models import CreatedVault, OpenVault, RecoveryShareVisualPaths
from .constants import ACCOUNT_USERNAME_MAX_LENGTH, APP_NAME, CREDENTIAL_FIELDS, MASTER_PASSWORD_MAX_LENGTH, MOCHA, SERVER_LOSS_MESSAGE, console
from .exceptions import ServerUnavailableDuringInteraction
from .forms import is_server_unreachable, prompt_entry, prompt_form, prompt_recovery_share, prompt_visual_share_paths, validate_absolute_visual_share_paths, validate_output_visual_share_paths
from .ui import confirm_action, error, mode_status, pause, select_menu, server_status_line, show_blocked_return, success, warn


class VaultCli:
    def __init__(self, service: VaultService | None = None) -> None:
        self.service = service or VaultService()
        self.vault: OpenVault | None = None

    def run(self) -> None:
        actions = {
            "create": self._create_vault,
            "open": self._open_vault,
        }
        while True:
            server_state.refresh()
            choice = select_menu(
                APP_NAME,
                "Distributed password manager with Shamir Secret Sharing and AES-128-GCM.",
                self._vault_menu_choices,
                status=server_status_line,
            )
            if choice in ("back", None):
                return
            actions[choice]()

    def _create_vault(self) -> None:
        try:
            username, password = self._credentials(
                require_server_online=True,
                validator=self._validate_create_vault_form,
            )
        except ServerUnavailableDuringInteraction:
            return
        if not username or not password:
            warn("username and master password are required")
            return
        try:
            created_vault = self.service.create_vault(username, password)
        except ValueError as exc:
            error(str(exc))
            return
        visual_paths = self._save_created_vault_visual_shares(created_vault)
        success("vault created. Save this recovery share and visual shares now.")
        console.print(f"[{MOCHA['green']}]{created_vault.recovery_share}[/{MOCHA['green']}]")
        console.print()
        console.print(f"[{MOCHA['subtext']}]share 1 saved to:[/{MOCHA['subtext']}] {visual_paths.share_one}")
        console.print(f"[{MOCHA['subtext']}]share 2 saved to:[/{MOCHA['subtext']}] {visual_paths.share_two}")
        console.print(
            f"[{MOCHA['subtext']}]temporary qr preview:[/{MOCHA['subtext']}] {created_vault.preview_paths.qr_code}"
        )
        console.print(
            f"[{MOCHA['subtext']}]temporary overlay preview:[/{MOCHA['subtext']}] {created_vault.preview_paths.overlay}"
        )
        pause()

    def _validate_create_vault_form(self, values: dict[str, str]) -> str | None:
        username = values["username"].strip()
        if not username:
            return None
        try:
            if self.service.username_exists(username):
                return "username already exists"
        except ValueError as exc:
            return str(exc)
        return None

    def _open_vault(self) -> None:
        app_state.clear_mode()
        credential_values = {"username": "", "password": ""}
        try:
            while True:
                result = prompt_form(
                    "Open vault",
                    "Fill username and master password.",
                    CREDENTIAL_FIELDS,
                    credential_values,
                    status=server_status_line,
                    field_limits={
                        "username": ACCOUNT_USERNAME_MAX_LENGTH,
                        "password": MASTER_PASSWORD_MAX_LENGTH,
                    },
                )
                if result is None:
                    return
                credential_values = result
                username = credential_values["username"]
                password = credential_values["password"]
                try:
                    local_share = self.service.unlock_local_share(username, password)
                except ValueError as exc:
                    error(str(exc))
                    pause()
                    continue
                if server_state.refresh().online:
                    app_state.set_mode("normal")
                    try:
                        self.vault = self.service.open_normal_with_local_share(username, local_share)
                    except ValueError as exc:
                        if is_server_unreachable(exc):
                            self._open_backup_after_unlock(username, local_share)
                            return
                        error(str(exc))
                        pause()
                        continue
                else:
                    self._open_backup_after_unlock(username, local_share)
                    return
                mode_status(self.vault.mode)
                pause()
                self._vault_loop()
                return
        finally:
            if self.vault is None:
                app_state.clear_mode()

    def _vault_loop(self) -> None:
        if self.vault is None:
            return
        handlers = {
            "add": self._add_entry,
            "edit": self._edit_entry,
            "delete": self._delete_entry,
            "view": self._view_entry,
        }
        try:
            while True:
                choice = select_menu(
                    f"{self.vault.username} vault ({self.vault.mode})",
                    "Backup mode is read-only." if self.vault.readonly else "Choose an operation.",
                    self._vault_actions(),
                    status=server_status_line,
                    abort_on_server_loss=self._requires_live_server(),
                )
                if choice in ("back", None):
                    return
                try:
                    handlers[choice]()
                except ValueError as exc:
                    if self._requires_live_server() and is_server_unreachable(exc):
                        show_blocked_return("Vault access", SERVER_LOSS_MESSAGE)
                        return
                    error(str(exc))
                    pause()
        except ServerUnavailableDuringInteraction:
            return
        finally:
            self.vault = None
            app_state.clear_mode()

    def _vault_actions(self) -> list[tuple[str, str]]:
        if self.vault is not None and self.vault.readonly:
            return [("view", "View entry"), ("back", "Back")]
        return [
            ("add", "Add entry"),
            ("edit", "Edit entry"),
            ("delete", "Delete entry"),
            ("view", "View entry"),
            ("back", "Back"),
        ]

    def _add_entry(self) -> None:
        entry = prompt_entry(require_server_online=self._requires_live_server())
        if self.vault is not None and entry is not None:
            self.service.add_entry(self.vault, entry)
            success("entry added")

    def _edit_entry(self) -> None:
        index = self._select_entry_index("Edit entry")
        if index is None:
            return
        entry = prompt_entry(self.vault.entries[index], require_server_online=self._requires_live_server())
        if entry is None:
            return
        self.service.update_entry(self.vault, index, entry)
        success("entry updated")

    def _delete_entry(self) -> None:
        index = self._select_entry_index("Delete entry")
        if index is None:
            return
        if self.vault is None:
            return
        entry = self.vault.entries[index]
        confirmed = confirm_action(
            "Delete entry",
            f"Delete {entry.service} ({entry.username})?",
            status=server_status_line,
            abort_on_server_loss=self._requires_live_server(),
        )
        if not confirmed:
            return
        self.service.delete_entry(self.vault, index)
        success("entry deleted")

    def _view_entry(self) -> None:
        if self.vault is None:
            return
        index = self._select_entry_index("View entry")
        if index is None:
            return
        entry = self.vault.entries[index]
        console.print()
        console.print(f"[bold {MOCHA['mauve']}]{entry.service}[/bold {MOCHA['mauve']}]")
        console.print(f"[{MOCHA['subtext']}]username:[/{MOCHA['subtext']}] {entry.username}")
        console.print(f"[{MOCHA['subtext']}]password:[/{MOCHA['subtext']}] {entry.password}")
        if entry.notes:
            console.print(f"[{MOCHA['subtext']}]notes:[/{MOCHA['subtext']}] {entry.notes}")
        pause()

    def _select_entry_index(self, title: str) -> int | None:
        if self.vault is None or not self.vault.entries:
            warn("no entries available")
            pause()
            return None
        choices = [(str(index), f"{entry.service} ({entry.username})") for index, entry in enumerate(self.vault.entries)]
        selected = select_menu(
            title,
            "Use arrow keys and enter.",
            choices,
            abort_on_server_loss=self._requires_live_server(),
        )
        if selected is None:
            return None
        return int(selected)

    def _credentials(
        self,
        require_server_online: bool = False,
        validator: Callable[[dict[str, str]], str | None] | None = None,
    ) -> tuple[str, str]:
        values = prompt_form(
            "Credentials",
            "Fill fields in any order.",
            CREDENTIAL_FIELDS,
            field_limits={
                "username": ACCOUNT_USERNAME_MAX_LENGTH,
                "password": MASTER_PASSWORD_MAX_LENGTH,
            },
            validator=validator,
            abort_on_server_loss=require_server_online,
        )
        if values is None:
            return "", ""
        return values["username"], values["password"]

    def _vault_menu_choices(self) -> list[tuple[str, str]]:
        online = server_state.snapshot().online
        choices = [("open", "Open vault"), ("back", "Back")]
        if online:
            choices.insert(0, ("create", "Create vault"))
        return choices

    def _requires_live_server(self) -> bool:
        return self.vault is not None and self.vault.mode == "normal"

    def _open_backup_after_unlock(self, username: str, local_share) -> None:
        app_state.set_mode("backup")
        while True:
            choice = select_menu(
                "Open vault",
                "Server unavailable. Choose how to submit the recovery share for backup mode.",
                [
                    ("text", "Submit recovery share text"),
                    ("visual", "Upload two visual share images"),
                    ("back", "Back"),
                ],
                status=server_status_line,
            )
            if choice in ("back", None):
                return
            if choice == "text":
                if self._open_backup_with_text(username, local_share):
                    return
                continue
            if self._open_backup_with_visual_shares(username, local_share):
                return

    def _open_backup_with_text(self, username: str, local_share) -> bool:
        def open_with_recovery_share(recovery_username: str, recovery_local_share, recovery_share: str) -> None:
            try:
                self.vault = self.service.open_backup_with_local_share(
                    recovery_username,
                    recovery_local_share,
                    recovery_share,
                )
            except ValueError:
                self.vault = None
                raise

        if not prompt_recovery_share(username, local_share, open_with_recovery_share):
            return False
        if self.vault is None:
            return False
        mode_status(self.vault.mode)
        pause()
        self._vault_loop()
        return True

    def _open_backup_with_visual_shares(self, username: str, local_share) -> bool:
        values = {"share_one": "", "share_two": ""}
        while True:
            result = prompt_visual_share_paths(
                "Open vault",
                "Upload both visual share images by providing their absolute file paths.",
                values,
                "absolute path",
                validator=validate_absolute_visual_share_paths,
            )
            if result is None:
                return False
            values = result
            try:
                self.vault = self.service.open_backup_with_visual_shares(
                    username,
                    local_share,
                    values["share_one"],
                    values["share_two"],
                )
            except ValueError as exc:
                error(str(exc))
                pause()
                continue
            mode_status(self.vault.mode)
            pause()
            self._vault_loop()
            return True

    def _save_created_vault_visual_shares(self, created_vault: CreatedVault) -> RecoveryShareVisualPaths:
        values = {"share_one": "", "share_two": ""}
        while True:
            result = prompt_visual_share_paths(
                "Save visual shares",
                "Provide absolute output paths for the two recovery share images.",
                values,
                "output path",
                validator=validate_output_visual_share_paths,
            )
            if result is None:
                warn("visual share output paths are required before vault creation can finish")
                pause()
                continue
            values = result
            try:
                return self.service.save_recovery_shares(
                    created_vault,
                    values["share_one"],
                    values["share_two"],
                )
            except ValueError as exc:
                error(str(exc))
                pause()


def run_client() -> None:
    VaultCli().run()