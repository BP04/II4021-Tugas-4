from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from server.database import Database


class RegisterRequest(BaseModel):
    username: str
    server_share: dict[str, Any]
    vault_blob: str
    vault_nonce: str


class UpdateVaultRequest(BaseModel):
    vault_blob: str
    vault_nonce: str


app = FastAPI(title="Distributed Password Manager API", version="0.1.0")
db = Database()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=5000, reload=False)
