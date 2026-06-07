import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_BIND_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 5000
DEFAULT_SERVER_DB_PATH = "data/server/vault.db"
DEFAULT_CLIENT_DATA_DIR = "data/client"


def server_host() -> str:
    return os.getenv("VAULT_SERVER_HOST", DEFAULT_SERVER_HOST)


def server_bind_host() -> str:
    return os.getenv("VAULT_SERVER_BIND_HOST", DEFAULT_SERVER_BIND_HOST)


def server_port() -> int:
    raw = os.getenv("VAULT_SERVER_PORT", str(DEFAULT_SERVER_PORT))
    return int(raw)


def server_url() -> str:
    return os.getenv("VAULT_SERVER_URL", f"http://{server_host()}:{server_port()}")


def server_db_path() -> str:
    return os.getenv("VAULT_SERVER_DB_PATH", DEFAULT_SERVER_DB_PATH)


def client_data_dir() -> str:
    return os.getenv("VAULT_CLIENT_DATA_DIR", DEFAULT_CLIENT_DATA_DIR)
