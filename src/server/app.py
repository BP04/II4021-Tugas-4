import base64

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from server.database import Database
from shared.config import server_bind_host, server_port


class RegisterRequest(BaseModel):
    username: str
    server_share: str
    vault_blob: str
    vault_nonce: str


class UpdateVaultRequest(BaseModel):
    vault_blob: str
    vault_nonce: str


app = FastAPI(title="Vault API", version="0.1.0")
db = Database()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: RegisterRequest) -> dict[str, str]:
    vault_blob, vault_nonce = _decode_vault_fields(payload.vault_blob, payload.vault_nonce)
    try:
        db.create_user(
            payload.username,
            payload.server_share,
            vault_blob,
            vault_nonce,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "created"}


@app.get("/users/{username}/share")
def load_server_share(username: str) -> dict[str, str]:
    try:
        server_share = db.load_server_share(username)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"server_share": server_share}


@app.get("/users/{username}/vault")
def load_vault(username: str) -> dict[str, str]:
    try:
        payload = db.load_vault_payload(username)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "vault": _b64e(payload["vault"]),
        "nonce": _b64e(payload["nonce"]),
    }


@app.put("/users/{username}/vault")
def update_vault(username: str, payload: UpdateVaultRequest) -> dict[str, str]:
    updated = db.update_vault(username, *_decode_vault_fields(payload.vault_blob, payload.vault_nonce))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="server user data not found")
    return {"status": "updated"}


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(data: str) -> bytes:
    try:
        return base64.b64decode(data.encode("ascii"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid base64 payload") from exc


def _decode_vault_fields(vault_blob: str, vault_nonce: str) -> tuple[bytes, bytes]:
    return _b64d(vault_blob), _b64d(vault_nonce)


if __name__ == "__main__":
    uvicorn.run("server.app:app", host=server_bind_host(), port=server_port(), reload=False)
