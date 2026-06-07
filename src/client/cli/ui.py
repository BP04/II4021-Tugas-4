import html
import os
import signal
import time
from threading import Timer
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from client.app_state import app_state
from client.server_state import HEARTBEAT_SECONDS
from .constants import DEFAULT_MENU_HINT, EXIT_CONFIRM_HINT, EXIT_CONFIRM_SECONDS, EXIT_HINT, MOCHA, RETURN_CHOICE, SERVER_LOSS_MESSAGE, console
from .exceptions import ServerUnavailableDuringInteraction

_CTRL_C_DEADLINE = 0.0
_MENU_SELECTIONS: dict[str, str] = {}


def select_menu(
    title: str,
    subtitle: str,
    choices: list[tuple[str, str]] | Callable[[], list[tuple[str, str]]],
    *,
    art: str | None = None,
    intro: str | None = None,
    hint: str = DEFAULT_MENU_HINT,
    clear: bool = True,
    status: Callable[[], str] | None = None,
    memory_key: str | None = None,
    abort_on_server_loss: bool = False,
    locked_message: str | None = None,
) -> str | None:
    if clear:
        clear_screen()
    menu_key = memory_key or title
    selected = _initial_menu_index(menu_key, _resolve_choices(choices))
    ctrl_c_deadline = 0.0
    initial_server_online = app_state.snapshot().server_online
    result = {"value": None, "interrupt": False, "server_lost": False}

    def current_choices() -> list[tuple[str, str]]:
        if current_locked_message() is not None:
            return [(RETURN_CHOICE, "Return")]
        return _resolve_choices(choices)

    def current_locked_message() -> str | None:
        if locked_message is not None:
            return locked_message
        if abort_on_server_loss and initial_server_online and not app_state.snapshot().server_online:
            return SERVER_LOSS_MESSAGE
        return None

    def server_lost() -> bool:
        return abort_on_server_loss and current_locked_message() is not None

    def clamp_selected() -> None:
        nonlocal selected
        options = current_choices()
        if not options:
            selected = 0
            return
        selected %= len(options)

    def render() -> HTML:
        clamp_selected()
        menu_choices = current_choices()
        active_exit_confirm = time.monotonic() <= ctrl_c_deadline
        footer = EXIT_CONFIRM_HINT if active_exit_confirm else hint
        footer_color = MOCHA["yellow"] if active_exit_confirm else MOCHA["overlay"]
        lines: list[str] = []
        lines.append(f"<style fg='{MOCHA['peach']}'>Welcome to {_html(title)}</style>")
        lines.append(f"<style fg='{MOCHA['subtext']}'>{'.' * 78}</style>")
        if art:
            lines.extend(_styled_art_lines(art))
            lines.append(f"<style fg='{MOCHA['subtext']}'>{'.' * 78}</style>")
        intro_text = intro or "Let's get started."
        lines.append(f"<style fg='{MOCHA['text']}'><b>{_html(intro_text)}</b></style>")
        lines.append(f"<style fg='{MOCHA['subtext']}'>{_html(subtitle)}</style>")
        if status:
            lines.append(status())
        if current_locked_message() is not None:
            lines.append(f"<style fg='{MOCHA['red']}'>{_html(current_locked_message())}</style>")
        lines.append("")
        for index, (_, label) in enumerate(menu_choices):
            pointer = ">" if index == selected else " "
            color = MOCHA["green"] if index == selected else MOCHA["text"]
            lines.append(f"<style fg='{color}'>{pointer} {index + 1}. {_html(label)}</style>")
        lines.append("")
        lines.append(f"<style fg='{footer_color}'>{_html(footer)}</style>")
        return HTML("\n".join(lines))

    control = FormattedTextControl(render, focusable=True)
    window = Window(content=control, always_hide_cursor=True)
    bindings = KeyBindings()

    @bindings.add("up")
    def _up(event) -> None:
        nonlocal selected
        if server_lost():
            return
        menu_choices = current_choices()
        selected = (selected - 1) % len(menu_choices)
        event.app.invalidate()

    @bindings.add("down")
    def _down(event) -> None:
        nonlocal selected
        if server_lost():
            return
        menu_choices = current_choices()
        selected = (selected + 1) % len(menu_choices)
        event.app.invalidate()

    @bindings.add("enter")
    def _enter(event) -> None:
        menu_choices = current_choices()
        result["value"] = menu_choices[selected][0]
        result["server_lost"] = server_lost()
        event.app.exit()

    @bindings.add("q")
    def _quit(event) -> None:
        if server_lost():
            return
        result["value"] = None
        event.app.exit()

    @bindings.add("c-c")
    def _ctrl_c(event) -> None:
        nonlocal ctrl_c_deadline
        now = time.monotonic()
        if now <= ctrl_c_deadline:
            result["interrupt"] = True
            event.app.exit()
            return
        ctrl_c_deadline = now + EXIT_CONFIRM_SECONDS
        timer = Timer(EXIT_CONFIRM_SECONDS, event.app.invalidate)
        timer.daemon = True
        timer.start()
        event.app.invalidate()

    app = Application(layout=Layout(HSplit([window])), key_bindings=bindings, full_screen=False)
    heartbeat_timer = _start_invalidator(app)
    app.run()
    heartbeat_timer.cancel()
    if result["interrupt"]:
        raise KeyboardInterrupt
    if result["server_lost"]:
        raise ServerUnavailableDuringInteraction(SERVER_LOSS_MESSAGE)
    menu_choices = current_choices()
    if menu_choices and current_locked_message() is None:
        _MENU_SELECTIONS[menu_key] = menu_choices[selected][0]
    return result["value"]


def show_blocked_return(title: str, message: str) -> None:
    select_menu(
        title,
        "Access to this page is blocked.",
        [],
        status=server_status_line,
        locked_message=message,
    )


def confirm_action(
    title: str,
    message: str,
    *,
    status: Callable[[], str] | None = None,
    abort_on_server_loss: bool = False,
) -> bool:
    choice = select_menu(
        title,
        message,
        [("yes", "Yes, continue"), ("no", "No, go back")],
        status=status,
        abort_on_server_loss=abort_on_server_loss,
    )
    return choice == "yes"


def prompt_input(label: str, password: bool = False, abort_on_server_loss: bool = False) -> str:
    initial_server_online = app_state.snapshot().server_online
    deadline = {"value": 0.0}
    session = PromptSession()
    bindings = KeyBindings()

    def toolbar() -> HTML:
        if abort_on_server_loss and initial_server_online and not app_state.snapshot().server_online:
            return HTML("<style fg='{0}'>server went offline. press enter to return</style>".format(MOCHA["red"]))
        active = time.monotonic() <= deadline["value"]
        text = EXIT_CONFIRM_HINT if active else f"enter submit | {EXIT_HINT}"
        color = MOCHA["yellow"] if active else MOCHA["overlay"]
        return HTML(f"<style fg='{color}'>{_html(text)}</style>")

    @bindings.add("c-c")
    def _ctrl_c(event) -> None:
        now = time.monotonic()
        if now <= deadline["value"]:
            event.app.exit(exception=KeyboardInterrupt)
            return
        deadline["value"] = now + EXIT_CONFIRM_SECONDS
        timer = Timer(EXIT_CONFIRM_SECONDS, event.app.invalidate)
        timer.daemon = True
        timer.start()
        event.app.invalidate()

    value = session.prompt(
        HTML(f"<style fg='{MOCHA['blue']}'><b>&gt;</b></style> {_html(label)}: "),
        is_password=password,
        bottom_toolbar=toolbar,
        key_bindings=bindings,
        refresh_interval=0.2,
    )
    if abort_on_server_loss and initial_server_online and not app_state.snapshot().server_online:
        raise ServerUnavailableDuringInteraction(SERVER_LOSS_MESSAGE)
    return value


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = prompt_input(f"{label}{suffix}")
    return value.strip() or default


def ask_int(
    label: str,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
    strict: bool = False,
) -> int | None:
    value = ask(label, str(default))
    try:
        parsed = int(value)
    except ValueError:
        return None if strict else default
    if minimum is not None and parsed < minimum:
        return None if strict else minimum
    if maximum is not None and parsed > maximum:
        return None if strict else maximum
    return parsed


def success(message: str) -> None:
    status_block("status", [("+", message, MOCHA["green"])])


def warn(message: str) -> None:
    status_block("warning", [("!", message, MOCHA["yellow"])])


def error(message: str) -> None:
    status_block("error", [("-", message, MOCHA["red"])])


def status_block(title: str, rows: list[tuple[str, str, str]]) -> None:
    console.print()
    console.print(f"[{MOCHA['overlay']}]{'.' * 78}[/{MOCHA['overlay']}]")
    console.print(f"[{MOCHA['overlay']}]  1[/] [bold {MOCHA['text']}]function[/] [bold {MOCHA['blue']}]{title}[/]() {{")
    for offset, (marker, message, color) in enumerate(rows, start=2):
        console.print(f"[{MOCHA['overlay']}]{offset:>3}[/] [{color}]{marker}  {message}[/{color}]")
    console.print(f"[{MOCHA['overlay']}]{len(rows) + 2:>3}[/] [bold {MOCHA['text']}]}}[/]")
    console.print(f"[{MOCHA['overlay']}]{'.' * 78}[/{MOCHA['overlay']}]")


def server_status_line() -> str:
    snapshot = app_state.snapshot()
    parts = []
    server_color = MOCHA["green"] if snapshot.server_online else MOCHA["red"]
    server_label = "active" if snapshot.server_online else "inactive"
    suffix = "" if snapshot.server_online else " | create vault disabled"
    parts.append(f"<style fg='{server_color}'>server: {server_label}</style>")
    if snapshot.access_mode is not None:
        mode_color = MOCHA["green"] if snapshot.access_mode == "normal" else MOCHA["yellow"]
        parts.append(f"<style fg='{MOCHA['overlay']}'> | </style>")
        parts.append(f"<style fg='{mode_color}'>mode: {snapshot.access_mode}</style>")
    if suffix:
        parts.append(f"<style fg='{MOCHA['overlay']}'>{suffix}</style>")
    return "".join(parts)


def mode_status(mode: str) -> None:
    color = MOCHA["green"] if mode == "normal" else MOCHA["yellow"]
    message = "normal mode: local share + server share" if mode == "normal" else "backup mode: local share + recovery share"
    status_block("access", [("*", message, color)])


def pause() -> None:
    prompt_input("Press enter to continue")


def install_ctrl_c_guard() -> None:
    signal.signal(signal.SIGINT, _handle_sigint)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _initial_menu_index(menu_key: str, choices: list[tuple[str, str]]) -> int:
    remembered = _MENU_SELECTIONS.get(menu_key)
    if remembered is None:
        return 0
    for index, (value, _) in enumerate(choices):
        if value == remembered:
            return index
    return 0


def _resolve_choices(choices: list[tuple[str, str]] | Callable[[], list[tuple[str, str]]]) -> list[tuple[str, str]]:
    if callable(choices):
        return choices()
    return choices


def _start_invalidator(app: Application) -> Timer:
    stopped = {"value": False}

    def invalidate() -> None:
        if stopped["value"]:
            return
        app.invalidate()
        timer = Timer(HEARTBEAT_SECONDS, invalidate)
        timer.daemon = True
        timer.start()

    timer = Timer(HEARTBEAT_SECONDS, invalidate)
    timer.daemon = True
    timer.start()
    original_cancel = timer.cancel

    def cancel() -> None:
        stopped["value"] = True
        original_cancel()

    timer.cancel = cancel
    return timer


def _styled_art_lines(art: str) -> list[str]:
    lines = []
    for line in art.strip("\n").splitlines():
        color = MOCHA["mauve"] if any(char in line for char in "()\\/") else MOCHA["blue"]
        lines.append(f"<style fg='{color}'>{_html(line)}</style>")
    return lines


def _html(value: str) -> str:
    return html.escape(value, quote=False)


def _handle_sigint(signum, frame) -> None:
    if _confirm_exit():
        raise KeyboardInterrupt


def _confirm_exit() -> bool:
    global _CTRL_C_DEADLINE
    now = time.monotonic()
    if now <= _CTRL_C_DEADLINE:
        return True
    _CTRL_C_DEADLINE = now + EXIT_CONFIRM_SECONDS
    status_block("exit", [("!", EXIT_CONFIRM_HINT, MOCHA["yellow"])])
    return False