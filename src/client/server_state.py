import threading
import time
from dataclasses import dataclass

from client.server_client import ServerClient

HEARTBEAT_SECONDS = 1.5


@dataclass(slots=True)
class ServerSnapshot:
    online: bool
    last_checked: float


class ServerState:
    def __init__(self, client: ServerClient | None = None) -> None:
        self.client = client or ServerClient()
        self._lock = threading.Lock()
        self._snapshot = ServerSnapshot(False, 0.0)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()

    def refresh(self) -> ServerSnapshot:
        snapshot = ServerSnapshot(self.client.is_available(), time.time())
        with self._lock:
            self._snapshot = snapshot
        return snapshot

    def snapshot(self) -> ServerSnapshot:
        with self._lock:
            return self._snapshot

    def _loop(self) -> None:
        while True:
            self.refresh()
            time.sleep(HEARTBEAT_SECONDS)


server_state = ServerState()