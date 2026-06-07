import os
from typing import Callable

from client.crypto import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, generate_password
from shared.models import VaultEntry
from .constants import ENTRY_NOTES_MAX_LENGTH, ENTRY_PASSWORD_MAX_LENGTH, ENTRY_SERVICE_MAX_LENGTH, ENTRY_USERNAME_MAX_LENGTH, FILE_PATH_MAX_LENGTH, FormField, RECOVERY_SHARE_MAX_LENGTH, SERVER_UNREACHABLE_PREFIX
from .ui import ask_int, error, pause, prompt_input, select_menu, server_status_line, warn

VISUAL_SHARE_FIELD_LIMITS = {
    "share_one": FILE_PATH_MAX_LENGTH,
    "share_two": FILE_PATH_MAX_LENGTH,
}


def prompt_entry(existing: VaultEntry | None = None, require_server_online: bool = False) -> VaultEntry | None:
    values = {
        "service": existing.service if existing else "",
        "username": existing.username if existing else "",
        "password": existing.password if existing else "",
        "notes": existing.notes if existing else "",
    }
    fields = [
        ("service", "Service", False, True),
        ("username", "Username/email", False, True),
        ("password", "Password", True, True),
        ("notes", "Notes", False, False),
    ]
    while True:
        result = prompt_form(
            "Password entry",
            "Choose a field to edit. Password setup is handled from the password field.",
            fields,
            values,
            [("save", "Save"), ("cancel", "Cancel")],
            abort_on_server_loss=require_server_online,
            password_option_fields={"password"},
            field_limits={
                "service": ENTRY_SERVICE_MAX_LENGTH,
                "username": ENTRY_USERNAME_MAX_LENGTH,
                "password": ENTRY_PASSWORD_MAX_LENGTH,
                "notes": ENTRY_NOTES_MAX_LENGTH,
            },
        )
        if result is None:
            return None
        return VaultEntry(
            service=result["service"],
            username=result["username"],
            password=result["password"],
            notes=result["notes"],
        )


def prompt_form(
    title: str,
    subtitle: str,
    fields: list[FormField] | Callable[[], list[FormField]],
    values: dict[str, str] | None = None,
    actions: list[tuple[str, str]] | None = None,
    status: Callable[[], str] | None = None,
    validator: Callable[[dict[str, str]], str | None] | None = None,
    abort_on_server_loss: bool = False,
    password_option_fields: set[str] | None = None,
    field_limits: dict[str, int] | None = None,
) -> dict[str, str] | tuple[str, dict[str, str]] | None:
    values = dict(values or {})
    actions = actions or [("save", "Save"), ("cancel", "Cancel")]
    for key, _, _, _ in _resolve_form_fields(fields):
        values.setdefault(key, "")
    while True:
        current_fields = _resolve_form_fields(fields)
        for key, _, _, _ in current_fields:
            values.setdefault(key, "")
        choice = select_menu(
            title,
            subtitle,
            lambda: _form_choices(_resolve_form_fields(fields), values, actions),
            status=status,
            abort_on_server_loss=abort_on_server_loss,
        )
        if choice is None or choice == "cancel":
            return None if actions[-1][0] == "cancel" else ("cancel", values)
        if choice.startswith("field:"):
            key = choice.removeprefix("field:")
            label, secret = _field_prompt(current_fields, key)
            if password_option_fields and key in password_option_fields:
                password_value = prompt_password_value(abort_on_server_loss=abort_on_server_loss)
                if password_value is None:
                    continue
                length_error = _length_error(label, password_value, field_limits.get(key) if field_limits else None)
                if length_error:
                    warn(length_error)
                    pause()
                    continue
                values[key] = password_value
                continue
            input_value = prompt_input(label, password=secret, abort_on_server_loss=abort_on_server_loss)
            length_error = _length_error(label, input_value, field_limits.get(key) if field_limits else None)
            if length_error:
                warn(length_error)
                pause()
                continue
            values[key] = input_value
            continue
        if choice == "save":
            missing = _missing_required(current_fields, values)
            if missing:
                warn("required fields missing: " + ", ".join(missing))
                pause()
                continue
            too_long = _too_long_fields(current_fields, values, field_limits or {})
            if too_long:
                warn("input too long: " + ", ".join(too_long))
                pause()
                continue
            if validator:
                validation_error = validator(values)
                if validation_error:
                    warn(validation_error)
                    pause()
                    continue
        if len(actions) == 2 and actions[0][0] == "save":
            return values
        return choice, values


def prompt_password_value(abort_on_server_loss: bool = False) -> str | None:
    while True:
        choice = select_menu(
            "Password options",
            "Choose how to set the password value.",
            [
                ("manual", "Input manual password"),
                ("generate", "Generate with CSPRNG"),
                ("back", "Back"),
            ],
            abort_on_server_loss=abort_on_server_loss,
        )
        if choice in ("back", None):
            return None
        if choice == "manual":
            return prompt_input("Password", password=True, abort_on_server_loss=abort_on_server_loss)
        length = ask_int(
            "Password length",
            16,
            minimum=MIN_PASSWORD_LENGTH,
            maximum=MAX_PASSWORD_LENGTH,
            strict=True,
        )
        if length is None:
            warn(f"password length must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH}")
            pause()
            continue
        try:
            return generate_password(length)
        except ValueError as exc:
            error(str(exc))
            pause()


def prompt_recovery_share(username: str, local_share, open_backup_with_local_share) -> bool:
    values = {"recovery": ""}
    while True:
        result = prompt_form(
            "Open vault",
            "Enter recovery share text to continue in backup mode.",
            [("recovery", "Recovery share", False, True)],
            values,
            status=server_status_line,
            field_limits={"recovery": RECOVERY_SHARE_MAX_LENGTH},
        )
        if result is None:
            return False
        values = result
        try:
            open_backup_with_local_share(username, local_share, values["recovery"])
        except ValueError as exc:
            error(str(exc))
            pause()
            continue
        return True


def prompt_visual_share_paths(
    title: str,
    subtitle: str,
    values: dict[str, str],
    path_suffix: str,
    validator: Callable[[dict[str, str]], str | None] | None = None,
) -> dict[str, str] | tuple[str, dict[str, str]] | None:
    return prompt_form(
        title,
        subtitle,
        [
            ("share_one", f"Visual share image 1 {path_suffix}", False, True),
            ("share_two", f"Visual share image 2 {path_suffix}", False, True),
        ],
        values,
        status=server_status_line,
        field_limits=VISUAL_SHARE_FIELD_LIMITS,
        validator=validator,
    )


def validate_absolute_visual_share_paths(values: dict[str, str]) -> str | None:
    for key in ("share_one", "share_two"):
        path = values.get(key, "").strip()
        if path and not os.path.isabs(path):
            return f"{key.replace('_', ' ')} must use an absolute path"
    return None


def validate_output_visual_share_paths(values: dict[str, str]) -> str | None:
    error_message = validate_absolute_visual_share_paths(values)
    if error_message:
        return error_message
    share_one = values.get("share_one", "").strip()
    share_two = values.get("share_two", "").strip()
    for key, path in (("share one", share_one), ("share two", share_two)):
        if not path:
            continue
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            return f"{key} output directory not found: {parent}"
        if os.path.exists(path):
            return f"{key} output file already exists: {path}"
    if share_one and share_two:
        normalized_one = os.path.normcase(os.path.normpath(share_one))
        normalized_two = os.path.normcase(os.path.normpath(share_two))
        if normalized_one == normalized_two:
            return "share one and share two must use different output paths"
    return None


def is_server_unreachable(exc: ValueError) -> bool:
    return SERVER_UNREACHABLE_PREFIX in str(exc)


def _form_choices(fields: list[FormField], values: dict[str, str], actions: list[tuple[str, str]]) -> list[tuple[str, str]]:
    choices = []
    for key, label, secret, required in fields:
        value = _display_value(values[key], secret)
        marker = "*" if required else " "
        choices.append((f"field:{key}", f"{label}{marker}: {value}"))
    choices.extend(actions)
    return choices


def _field_prompt(fields: list[FormField], key: str) -> tuple[str, bool]:
    for field_key, label, secret, _ in fields:
        if field_key == key:
            return label, secret
    raise ValueError("unknown form field")


def _missing_required(fields: list[FormField], values: dict[str, str]) -> list[str]:
    return [label for key, label, _, required in fields if required and not values[key].strip()]


def _too_long_fields(fields: list[FormField], values: dict[str, str], field_limits: dict[str, int]) -> list[str]:
    return [
        f"{label} (max {field_limits[key]})"
        for key, label, _, _ in fields
        if key in field_limits and len(values[key]) > field_limits[key]
    ]


def _length_error(label: str, value: str, max_length: int | None) -> str | None:
    if max_length is None or len(value) <= max_length:
        return None
    return f"{label} must be at most {max_length} characters"


def _display_value(value: str, secret: bool) -> str:
    if not value:
        return "[empty]"
    if secret:
        return "*" * min(len(value), 12)
    return value


def _resolve_form_fields(fields: list[FormField] | Callable[[], list[FormField]]) -> list[FormField]:
    if callable(fields):
        return fields()
    return fields