from rich.console import Console

from client.app_state import app_state
from client.cli.commands import MAIN_MENU_HINT, WELCOME_ART, install_ctrl_c_guard, run_client, select_menu, server_status_line
from client.server_state import server_state

APP_NAME = "Vault"
console = Console()


class Launcher:
    def run(self) -> None:
        while True:
            choice = select_menu(
                APP_NAME,
                "Welcome back. Choose where you want to go.",
                [
                    ("client", "Open client"),
                    ("quit", "Quit"),
                ],
                art=WELCOME_ART,
                hint=MAIN_MENU_HINT,
                status=server_status_line,
            )
            if choice in ("quit", None):
                return
            run_client()


def main() -> None:
    install_ctrl_c_guard()
    server_state.start()
    app_state.clear_mode()
    try:
        Launcher().run()
    except KeyboardInterrupt:
        console.print()
        console.print("[dim]quit[/dim]")


if __name__ == "__main__":
    main()