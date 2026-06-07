import uvicorn

from .app import app
from shared.config import server_bind_host, server_port


def run_server() -> None:
    uvicorn.run("server.app:app", host=server_bind_host(), port=server_port(), reload=False)


__all__ = ["app", "run_server"]