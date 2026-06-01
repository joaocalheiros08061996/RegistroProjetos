import os
from dataclasses import dataclass
from typing import Mapping

from cryptography.fernet import Fernet, InvalidToken


PAYLOAD_VERSION = "v1"


class SecretCryptoError(ValueError):
    pass


@dataclass(frozen=True)
class SecretEncryptor:
    active_key_id: str
    keys: Mapping[str, Fernet]

    @classmethod
    def from_env(cls) -> "SecretEncryptor":
        active_key_id = os.getenv("DATA_ENCRYPTION_ACTIVE_KEY_ID", "").strip()
        raw_keys = os.getenv("DATA_ENCRYPTION_KEYS", "").strip()
        return cls.from_config(active_key_id=active_key_id, raw_keys=raw_keys)

    @classmethod
    def from_config(cls, *, active_key_id: str, raw_keys: str) -> "SecretEncryptor":
        key_id = active_key_id.strip()
        keys = _parse_keys(raw_keys)

        if not key_id:
            raise SecretCryptoError("DATA_ENCRYPTION_ACTIVE_KEY_ID nao configurada.")
        if key_id not in keys:
            raise SecretCryptoError("Chave ativa nao encontrada em DATA_ENCRYPTION_KEYS.")

        return cls(active_key_id=key_id, keys=keys)

    def encrypt_text(self, value: str) -> str:
        if not isinstance(value, str):
            raise SecretCryptoError("Valor para criptografia deve ser texto.")

        ciphertext = self.keys[self.active_key_id].encrypt(value.encode("utf-8"))
        return f"{PAYLOAD_VERSION}:{self.active_key_id}:{ciphertext.decode('utf-8')}"

    def decrypt_text(self, payload: str) -> str:
        version, key_id, ciphertext = _split_payload(payload)
        if version != PAYLOAD_VERSION:
            raise SecretCryptoError("Versao de payload criptografado nao suportada.")

        fernet = self.keys.get(key_id)
        if fernet is None:
            raise SecretCryptoError("Chave de descriptografia nao encontrada.")

        try:
            plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise SecretCryptoError("Payload criptografado invalido.") from exc

        return plaintext.decode("utf-8")


def encrypt_secret(value: str) -> str:
    return SecretEncryptor.from_env().encrypt_text(value)


def decrypt_secret(payload: str) -> str:
    return SecretEncryptor.from_env().decrypt_text(payload)


def _parse_keys(raw_keys: str) -> dict[str, Fernet]:
    if not raw_keys:
        raise SecretCryptoError("DATA_ENCRYPTION_KEYS nao configurada.")

    parsed: dict[str, Fernet] = {}
    for item in raw_keys.split(","):
        key_id, separator, key_value = item.partition(":")
        key_id = key_id.strip()
        key_value = key_value.strip()

        if not separator or not key_id or not key_value:
            raise SecretCryptoError("DATA_ENCRYPTION_KEYS deve usar key_id:fernet_key.")

        try:
            parsed[key_id] = Fernet(key_value.encode("utf-8"))
        except Exception as exc:
            raise SecretCryptoError("Chave Fernet invalida em DATA_ENCRYPTION_KEYS.") from exc

    return parsed


def _split_payload(payload: str) -> tuple[str, str, str]:
    if not isinstance(payload, str):
        raise SecretCryptoError("Payload criptografado deve ser texto.")

    version, separator, remainder = payload.partition(":")
    key_id, second_separator, ciphertext = remainder.partition(":")
    if not separator or not second_separator or not version or not key_id or not ciphertext:
        raise SecretCryptoError("Formato de payload criptografado invalido.")

    return version, key_id, ciphertext
