from pathlib import Path

from cryptography.fernet import Fernet
from fastapi import Response
import pytest

from api.main import _apply_security_headers
from infra.security.crypto import SecretCryptoError, SecretEncryptor, decrypt_secret, encrypt_secret


def test_production_http_request_redirects_to_https(client, monkeypatch):
    monkeypatch.setenv("ENV", "production")
    response = client.get(
        "/app/login.html",
        headers={"x-forwarded-proto": "http", "host": "example.com"},
        follow_redirects=False,
    )

    assert response.status_code == 308
    assert response.headers["location"] == "https://example.com/app/login.html"
    assert "max-age=31536000" in response.headers["strict-transport-security"]


def test_local_http_request_does_not_redirect(client, monkeypatch):
    monkeypatch.setenv("ENV", "test")
    response = client.get(
        "/app/login.html",
        headers={"x-forwarded-proto": "http", "host": "localhost"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "strict-transport-security" not in response.headers


def test_security_headers_are_added(client):
    response = client.get("/app/login.html")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "microphone=()" in response.headers["permissions-policy"]

    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' https://cdn.plot.ly 'unsafe-eval'" in csp
    assert "script-src-attr 'none'" in csp
    assert "object-src 'none'" in csp
    assert "frame-src 'none'" in csp
    assert "'unsafe-inline'" not in _csp_directive(csp, "script-src")


def test_security_headers_are_added_to_json_and_not_found_responses(client):
    json_response = client.get("/app/config")
    missing_response = client.get("/missing-route")

    assert json_response.status_code == 200
    assert missing_response.status_code == 404
    for response in (json_response, missing_response):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["permissions-policy"]
        assert response.headers["content-security-policy"]


def test_frontend_config_exposes_public_privacy_metadata_without_audit_secret(
    client,
    monkeypatch,
):
    monkeypatch.setenv("PRIVACY_CONTROLLER_NAME", "Controlador de Teste")
    monkeypatch.setenv("PRIVACY_CONTACT_EMAIL", "privacidade@example.com")
    monkeypatch.setenv("PRIVACY_POLICY_VERSION", "2026-06-01")
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "nao-expor")

    response = client.get("/app/config")

    assert response.status_code == 200
    assert response.json()["privacy_controller_name"] == "Controlador de Teste"
    assert response.json()["privacy_contact_email"] == "privacidade@example.com"
    assert response.json()["privacy_policy_version"] == "2026-06-01"
    assert "privacy_audit_hash_secret" not in response.json()
    assert "nao-expor" not in response.text


def test_security_headers_strip_stack_identification():
    response = Response(
        headers={
            "Server": "uvicorn",
            "X-Powered-By": "framework",
        }
    )

    hardened = _apply_security_headers(response, include_hsts=False)

    assert "server" not in hardened.headers
    assert "x-powered-by" not in hardened.headers


def test_docker_disables_uvicorn_server_header():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "--no-server-header" in dockerfile


def _csp_directive(csp: str, directive: str) -> str:
    for item in csp.split(";"):
        normalized = item.strip()
        if normalized == directive or normalized.startswith(f"{directive} "):
            return normalized
    return ""


def test_secret_encryptor_encrypts_and_decrypts_text():
    key = Fernet.generate_key().decode("utf-8")
    encryptor = SecretEncryptor.from_config(
        active_key_id="primary",
        raw_keys=f"primary:{key}",
    )

    payload = encryptor.encrypt_text("valor-sensivel")

    assert payload.startswith("v1:primary:")
    assert "valor-sensivel" not in payload
    assert encryptor.decrypt_text(payload) == "valor-sensivel"


def test_secret_encryptor_requires_keys(monkeypatch):
    monkeypatch.delenv("DATA_ENCRYPTION_ACTIVE_KEY_ID", raising=False)
    monkeypatch.delenv("DATA_ENCRYPTION_KEYS", raising=False)

    with pytest.raises(SecretCryptoError):
        encrypt_secret("valor")


def test_secret_encryptor_rejects_unknown_key_id():
    key = Fernet.generate_key().decode("utf-8")
    other_key = Fernet.generate_key().decode("utf-8")
    ciphertext = Fernet(other_key.encode("utf-8")).encrypt(b"valor").decode("utf-8")
    encryptor = SecretEncryptor.from_config(
        active_key_id="primary",
        raw_keys=f"primary:{key}",
    )

    with pytest.raises(SecretCryptoError):
        encryptor.decrypt_text(f"v1:missing:{ciphertext}")


def test_secret_encryptor_supports_key_rotation(monkeypatch):
    old_key = Fernet.generate_key().decode("utf-8")
    new_key = Fernet.generate_key().decode("utf-8")

    old_encryptor = SecretEncryptor.from_config(
        active_key_id="previous",
        raw_keys=f"previous:{old_key}",
    )
    old_payload = old_encryptor.encrypt_text("segredo-antigo")

    monkeypatch.setenv("DATA_ENCRYPTION_ACTIVE_KEY_ID", "primary")
    monkeypatch.setenv("DATA_ENCRYPTION_KEYS", f"primary:{new_key},previous:{old_key}")

    assert decrypt_secret(old_payload) == "segredo-antigo"

    new_payload = encrypt_secret("segredo-novo")
    assert new_payload.startswith("v1:primary:")
    assert decrypt_secret(new_payload) == "segredo-novo"
