from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, db_path: str = "data/server/vault.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    server_share TEXT NOT NULL,
                    vault_blob TEXT NOT NULL,
                    vault_nonce TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_user(
        self,
        username: str,
        server_share: dict[str, Any],
        vault_blob: str,
        vault_nonce: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (username, server_share, vault_blob, vault_nonce) VALUES (?, ?, ?, ?)",
                (username, json.dumps(server_share), vault_blob, vault_nonce),
            )
            conn.commit()

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT username, server_share, vault_blob, vault_nonce FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                return None
            return {
                "username": row["username"],
                "server_share": json.loads(row["server_share"]),
                "vault_blob": row["vault_blob"],
                "vault_nonce": row["vault_nonce"],
            }

    def update_vault(self, username: str, vault_blob: str, vault_nonce: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE users SET vault_blob = ?, vault_nonce = ? WHERE username = ?",
                (vault_blob, vault_nonce, username),
            )
            conn.commit()
            return cursor.rowcount > 0
