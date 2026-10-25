import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key(name: str) -> bytes:
    value = os.getenv(name, "")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError(
            f"Configure {name} como uma chave Base64 aleatÃ³ria de 32 bytes."
        ) from error
    if len(decoded) != 32:
        raise RuntimeError(f"Configure {name} como uma chave Base64 aleatÃ³ria de 32 bytes.")
    return decoded


def encrypt_personal_data(value: str) -> bytes:
    version = int(os.getenv("AUTH_ENCRYPTION_KEY_VERSION", "1"))
    if version < 1 or version > 255:
        raise RuntimeError("AUTH_ENCRYPTION_KEY_VERSION deve estar entre 1 e 255.")
    nonce = os.urandom(12)
    key_name = f"AUTH_ENCRYPTION_KEY_V{version}"
    if version == 1 and not os.getenv(key_name):
        key_name = "AUTH_ENCRYPTION_KEY"
    ciphertext = AESGCM(_key(key_name)).encrypt(
        nonce, value.encode("utf-8"), f"expenses:user:v{version}".encode()
    )
    return bytes([version]) + nonce + ciphertext


def decrypt_personal_data(value: bytes) -> str:
    version = value[0]
    key_name = f"AUTH_ENCRYPTION_KEY_V{version}"
    if version == 1 and not os.getenv(key_name):
        key_name = "AUTH_ENCRYPTION_KEY"
    nonce, ciphertext = value[1:13], value[13:]
    return (
        AESGCM(_key(key_name))
        .decrypt(nonce, ciphertext, f"expenses:user:v{version}".encode())
        .decode("utf-8")
    )


def lookup_digest(value: str, *, namespace: str = "email") -> str:
    normalized = value.strip().casefold()
    return hmac.new(
        _key("AUTH_LOOKUP_KEY"), f"{namespace}:{normalized}".encode("utf-8"), hashlib.sha256
    ).hexdigest()


def token_digest(token: str) -> str:
    return hmac.new(
        _key("AUTH_LOOKUP_KEY"), f"refresh:{token}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
