from rich.console import Console

from client.crypto import MAX_PASSWORD_LENGTH

FormField = tuple[str, str, bool, bool]

console = Console()
APP_NAME = "Vault"
EXIT_CONFIRM_SECONDS = 3
EXIT_HINT = "ctrl+c quit"
EXIT_CONFIRM_HINT = f"press ctrl+c again within {EXIT_CONFIRM_SECONDS}s to quit"
DEFAULT_MENU_HINT = f"up/down move | enter select | q back | {EXIT_HINT}"
MAIN_MENU_HINT = f"up/down move | enter select | {EXIT_HINT}"
RETURN_CHOICE = "__return__"
SERVER_LOSS_MESSAGE = "Server went offline. Return to the vault access page."
SERVER_UNREACHABLE_PREFIX = "server is not reachable"
ACCOUNT_USERNAME_MAX_LENGTH = 64
MASTER_PASSWORD_MAX_LENGTH = MAX_PASSWORD_LENGTH
RECOVERY_SHARE_MAX_LENGTH = 2048
FILE_PATH_MAX_LENGTH = 1024
ENTRY_SERVICE_MAX_LENGTH = 100
ENTRY_USERNAME_MAX_LENGTH = 254
ENTRY_PASSWORD_MAX_LENGTH = 512
ENTRY_NOTES_MAX_LENGTH = 2000

CREDENTIAL_FIELDS: list[FormField] = [
    ("username", "Username", False, True),
    ("password", "Master password", True, True),
]

MOCHA = {
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "overlay": "#6c7086",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "mauve": "#cba6f7",
    "peach": "#fab387",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
}

WELCOME_ART = r"""
        *                         *

              _________
         ____/  _____  \____              .-.
        /   _  /     \  _   \            (   )
       /___/ \_\_____/ /_\___\            `-'

    *             .----.                         *
                 / .--. \
                / /____\ \
                \________/

          .-.
         (o o)       *
        /|   |\
         |___|
         /   \
"""