import hashlib
import hmac
import os


class PrivacyAuditConfigError(RuntimeError):
    pass


def configured_policy_version(explicit_value: str | None = None) -> str:
    policy_version = str(
        explicit_value
        if explicit_value is not None
        else os.getenv("PRIVACY_POLICY_VERSION", "")
    ).strip()
    if not policy_version:
        raise PrivacyAuditConfigError("PRIVACY_POLICY_VERSION nao configurada.")
    if len(policy_version) > 120:
        raise PrivacyAuditConfigError("PRIVACY_POLICY_VERSION excede 120 caracteres.")
    return policy_version


def configured_audit_hash_secret() -> str:
    secret = os.getenv("PRIVACY_AUDIT_HASH_SECRET", "").strip()
    if not secret:
        raise PrivacyAuditConfigError("PRIVACY_AUDIT_HASH_SECRET nao configurada.")
    return secret


def privacy_audit_hash(value: str) -> str:
    secret = configured_audit_hash_secret()
    return hmac.new(
        secret.encode("utf-8"),
        str(value or "").strip().lower().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
