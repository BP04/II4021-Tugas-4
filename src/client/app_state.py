import threading
from dataclasses import dataclass

from client.server_state import server_state


@dataclass(slots=True)
class AppSnapshot:
    server_online: bool
    access_mode: str | None


class AppState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._access_mode: str | None = None

    def set_mode(self, mode: str | None) -> AppSnapshot:
        with self._lock:
            self._access_mode = mode
        return self.snapshot()

    def clear_mode(self) -> AppSnapshot:
        return self.set_mode(None)

    def snapshot(self) -> AppSnapshot:
        server_online = server_state.snapshot().online
        with self._lock:
            access_mode = self._access_mode
        return AppSnapshot(server_online=server_online, access_mode=access_mode)


app_state = AppState()