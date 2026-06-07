import sqlite3
from contextlib import contextmanager
from pathlib import Path

from shared.config import server_db_path


class Database:
    def __init__(self, db_path: str | None = None) -> None:
        db_path = db_path or server_db_path()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def create_user(
        self,
        username: str,
        server_share: str,
        vault_blob: bytes,
        vault_nonce: bytes,
    ) -> None:
        try:
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO users (username, server_share, vault_blob, vault_nonce)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, server_share, vault_blob, vault_nonce),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("server user already exists") from exc

    def get_user(self, username: str) -> dict[str, bytes | str] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT username, server_share, vault_blob, vault_nonce FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return {
            "username": str(row["username"]),
            "server_share": str(row["server_share"]),
            "vault_blob": bytes(row["vault_blob"]),
            "vault_nonce": bytes(row["vault_nonce"]),
        }

    def load_server_share(self, username: str) -> str:
        row = self._require_user(username)
        return str(row["server_share"])

    def load_vault_payload(self, username: str) -> dict[str, bytes]:
        row = self._require_user(username)
        return {
            "vault": bytes(row["vault_blob"]),
            "nonce": bytes(row["vault_nonce"]),
        }

    def update_vault(self, username: str, vault_blob: bytes, vault_nonce: bytes) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE users
                SET vault_blob = ?, vault_nonce = ?, updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
                """,
                (vault_blob, vault_nonce, username),
            )
        return cursor.rowcount > 0

    def is_available(self) -> bool:
        try:
            with self._connect() as db:
                db.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    server_share TEXT NOT NULL,
                    vault_blob BLOB NOT NULL,
                    vault_nonce BLOB NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def _require_user(self, username: str) -> sqlite3.Row:
        with self._connect() as db:
            row = db.execute(
                "SELECT username, server_share, vault_blob, vault_nonce FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            raise ValueError("server user data not found")
        return row

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()
