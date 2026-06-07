import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12


def generate_key(length: int = 16) -> bytes:
    return os.urandom(length)


def encrypt_bytes(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return ciphertext, nonce


def decrypt_bytes(key: bytes, ciphertext: bytes, nonce: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise ValueError("decryption failed") from exc


def encrypt(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    return encrypt_bytes(key, plaintext)


def decrypt(key: bytes, ciphertext: bytes, nonce: bytes) -> bytes:
    return decrypt_bytes(key, ciphertext, nonce)