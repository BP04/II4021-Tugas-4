import os

from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

KDF_NAME = "argon2id"
SALT_BYTES = 16
KEY_BYTES = 16
ARGON2_ITERATIONS = 3
ARGON2_LANES = 4
ARGON2_MEMORY_COST = 64 * 1024


def generate_salt(length: int = SALT_BYTES) -> bytes:
    return os.urandom(length)


def new_salt() -> bytes:
    return generate_salt()


def derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = Argon2id(
        salt=salt,
        length=KEY_BYTES,
        iterations=ARGON2_ITERATIONS,
        lanes=ARGON2_LANES,
        memory_cost=ARGON2_MEMORY_COST,
    )
    return kdf.derive(master_password.encode("utf-8"))


def kdf_params() -> dict[str, int | str]:
    return {
        "name": KDF_NAME,
        "iterations": ARGON2_ITERATIONS,
        "lanes": ARGON2_LANES,
        "memory_cost": ARGON2_MEMORY_COST,
        "length": KEY_BYTES,
    }