import os
import string

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

DEFAULT_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{};:,.?"
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
CHACHA20_KEY_BYTES = 32
CHACHA20_NONCE_BYTES = 16
CHACHA20_BLOCK_BYTES = 64


def generate_password(length: int) -> str:
    if length < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password length must be at least {MIN_PASSWORD_LENGTH}")
    if length > MAX_PASSWORD_LENGTH:
        raise ValueError(f"password length must be at most {MAX_PASSWORD_LENGTH}")
    alphabet_size = len(DEFAULT_ALPHABET)
    threshold = 256 - (256 % alphabet_size)
    chars: list[str] = []
    stream = _chacha20_stream()
    while len(chars) < length:
        for byte in stream:
            if byte >= threshold:
                continue
            chars.append(DEFAULT_ALPHABET[byte % alphabet_size])
            if len(chars) == length:
                return "".join(chars)
        stream = _chacha20_stream()
    return "".join(chars)


def _chacha20_stream(size: int = CHACHA20_BLOCK_BYTES * 4) -> bytes:
    key = os.urandom(CHACHA20_KEY_BYTES)
    nonce = os.urandom(CHACHA20_NONCE_BYTES)
    cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None)
    encryptor = cipher.encryptor()
    return encryptor.update(b"\x00" * size)