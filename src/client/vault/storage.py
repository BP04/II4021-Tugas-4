from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any


class ClientStorage:
    def __init__(self, base_dir: str = "data/client") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
