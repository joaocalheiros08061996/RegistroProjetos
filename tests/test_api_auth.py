import time

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
import pytest

import api.auth_controller as auth_controller
import api.deps as deps

def _set_refresh_session_cookie(
    client,
    refresh_token: str,
    *,
    issued_at: int | None = None,
    last_seen_at: int | None = None,
    session_id: str = "session-1",
):
    now = int(time.time())
    session = auth_controller._AuthSession(
        session_id=session_id,
        issued_at=issued_at if issued_at is not None else now,
        last_seen_at=last_seen_at if last_seen_at is not None else now,
        refresh_token_hash=auth_controller._token_hash(refresh_token),
    )
    client.cookies.set("refresh_token", refresh_token, path="/auth")
    client.cookies.set(
        "auth_session",
        auth_controller._encode_session(session),
        path="/auth",
    )
    return session


def test_login_endpoint_maps_path_and_payload(client, monkeypatch):
    captured = {}

    def fake_call(path, payload):
        captured["path"] = path
        captured["email"] = payload.email
        captured["password"] = payload.password
        return {"access_token": "token-123"}

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    response = client.post(
        "/auth/login",
        json={"email": "joao@example.com", "password": "123456"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-123"
    assert captured["path"] == "token?grant_type=password"
    assert captured["email"] == "joao@example.com"
    assert captured["password"] == "123456"


def test_signup_endpoint_maps_path_sets_cookie_and_hides_refresh_token(client, monkeypatch):
    captured = {}

    def fake_call(path, payload):
        captured["path"] = path
        captured["email"] = payload.email
        return {
            "access_token": "signup-access",
            "refresh_token": "signup-refresh",
            "user": {"id": "user-1", "email": payload.email},
        }

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)
    monkeypatch.setattr(
        auth_controller,
        "_record_signup_privacy_acknowledgement",
        lambda **kwargs: captured.update({"privacy": kwargs}),
    )

    response = client.post(
        "/auth/signup",
        json={
            "email": "joao@example.com",
            "password": "123456",
            "privacy_notice_acknowledged": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "signup-access",
        "user": {"id": "user-1", "email": "joao@example.com"},
    }
    assert captured["path"] == "signup"
    assert captured["email"] == "joao@example.com"
    assert captured["privacy"] == {
        "user_id": "user-1",
        "email": "joao@example.com",
        "client_ip": "testclient",
        "policy_version": "2026-06-01",
    }
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=signup-refresh" in set_cookie
    assert "auth_session=" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.parametrize("value", [None, False])
def test_signup_requires_privacy_notice_acknowledgement(client, value):
    payload = {"email": "joao@example.com", "password": "123456"}
    if value is not None:
        payload["privacy_notice_acknowledged"] = value

    response = client.post("/auth/signup", json=payload)

    assert response.status_code == 422


def test_signup_forwards_only_credentials_and_records_minimized_audit_data(
    client,
    monkeypatch,
):
    captured = {}

    def fake_post(path, payload, *, bearer_token=None, generic_auth_error=False):
        captured["supabase_payload"] = payload
        return {"user": {"id": "user-1", "email": payload["email"]}}

    class FakePrivacyRepository:
        def record_signup_acknowledgement(self, **kwargs):
            captured["privacy"] = kwargs

    monkeypatch.setattr(auth_controller, "_post_supabase_auth", fake_post)
    monkeypatch.setattr(
        auth_controller,
        "SupabasePrivacyAcknowledgementRepository",
        FakePrivacyRepository,
    )

    response = client.post(
        "/auth/signup",
        headers={"X-Forwarded-For": "192.0.2.10"},
        json={
            "email": "joao@example.com",
            "password": "123456",
            "privacy_notice_acknowledged": True,
        },
    )

    assert response.status_code == 200
    assert captured["supabase_payload"] == {
        "email": "joao@example.com",
        "password": "123456",
    }
    assert captured["privacy"]["user_id"] == "user-1"
    assert captured["privacy"]["policy_version"] == "2026-06-01"
    assert captured["privacy"]["email_hash"] == auth_controller._privacy_audit_hash(
        "joao@example.com"
    )
    assert captured["privacy"]["ip_hash"] == auth_controller._privacy_audit_hash(
        "192.0.2.10"
    )
    assert "joao@example.com" not in captured["privacy"].values()
    assert "192.0.2.10" not in captured["privacy"].values()


def test_signup_audit_failure_returns_503_without_auth_cookies(client, monkeypatch):
    def fake_call(path, payload):
        return {
            "access_token": "signup-access",
            "refresh_token": "signup-refresh",
            "user": {"id": "user-1", "email": payload.email},
        }

    def fail_audit(**kwargs):
        raise HTTPException(status_code=503, detail="Falha de auditoria")

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)
    monkeypatch.setattr(
        auth_controller,
        "_record_signup_privacy_acknowledgement",
        fail_audit,
    )

    response = client.post(
        "/auth/signup",
        json={
            "email": "joao@example.com",
            "password": "123456",
            "privacy_notice_acknowledged": True,
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Falha de auditoria"
    assert "refresh_token=" not in response.headers.get("set-cookie", "")
    assert "auth_session=" not in response.headers.get("set-cookie", "")


def test_signup_rejects_malformed_email(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "joao@@example",
            "password": "123456",
            "privacy_notice_acknowledged": True,
        },
    )

    assert response.status_code == 422


def test_signup_rejects_short_password(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "joao@example.com",
            "password": "12345",
            "privacy_notice_acknowledged": True,
        },
    )

    assert response.status_code == 422


def test_login_endpoint_propagates_http_error(client, monkeypatch):
    def fake_call(path, payload):
        raise HTTPException(status_code=503, detail="Falha de rede")

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    response = client.post(
        "/auth/login",
        json={"email": "joao@example.com", "password": "123456"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Falha de rede"


def test_login_sets_refresh_cookie_and_hides_refresh_token(client, monkeypatch):
    def fake_call(path, payload):
        return {
            "access_token": "access-123",
            "refresh_token": "refresh-123",
            "expires_in": 3600,
            "user": {"id": "user-1", "email": payload.email},
        }

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    response = client.post(
        "/auth/login",
        json={"email": "joao@example.com", "password": "123456"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-123",
        "expires_in": 3600,
        "user": {"id": "user-1", "email": "joao@example.com"},
    }
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=refresh-123" in set_cookie
    assert "auth_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_login_sets_secure_auth_cookies_when_enabled(client, monkeypatch):
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")

    def fake_call(path, payload):
        return {
            "access_token": "access-123",
            "refresh_token": "refresh-123",
        }

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    response = client.post(
        "/auth/login",
        json={"email": "joao@example.com", "password": "123456"},
    )

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=refresh-123" in set_cookie
    assert "auth_session=" in set_cookie
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_refresh_requires_refresh_cookie(client):
    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token ausente."
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_refresh_uses_cookie_and_rotates_refresh_token(client, monkeypatch):
    captured = {}

    def fake_post(path, payload, *, bearer_token=None, generic_auth_error=False):
        captured["path"] = path
        captured["payload"] = payload
        captured["generic_auth_error"] = generic_auth_error
        return {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
        }

    monkeypatch.setattr(auth_controller, "_post_supabase_auth", fake_post)
    previous_session = _set_refresh_session_cookie(client, "old-refresh")

    response = client.post("/auth/refresh")

    assert response.status_code == 200
    assert response.json() == {"access_token": "new-access"}
    assert captured["path"] == "token?grant_type=refresh_token"
    assert captured["payload"] == {"refresh_token": "old-refresh"}
    assert captured["generic_auth_error"] is True
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=new-refresh" in set_cookie
    assert "auth_session=" in set_cookie
    current_session = auth_controller._decode_session(response.cookies["auth_session"])
    assert current_session.session_id != previous_session.session_id
    assert current_session.issued_at == previous_session.issued_at
    assert current_session.refresh_token_hash == auth_controller._token_hash("new-refresh")


def test_refresh_requires_signed_session_cookie(client):
    client.cookies.set("refresh_token", "refresh-without-session", path="/auth")

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Sessao de refresh ausente."
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_refresh_rejects_session_expired_by_inactivity(client):
    now = int(time.time())
    _set_refresh_session_cookie(
        client,
        "old-refresh",
        last_seen_at=now - auth_controller.AUTH_SESSION_IDLE_TIMEOUT_SECONDS - 1,
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Sessao expirada por inatividade."
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_refresh_rejects_session_expired_by_absolute_timeout(client):
    now = int(time.time())
    _set_refresh_session_cookie(
        client,
        "old-refresh",
        issued_at=now - auth_controller.AUTH_SESSION_ABSOLUTE_TIMEOUT_SECONDS - 1,
        last_seen_at=now,
    )

    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json()["detail"] == "Sessao expirada."
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_logout_clears_refresh_cookie_and_attempts_supabase_logout(client, monkeypatch):
    captured = {}

    def fake_post(path, payload, *, bearer_token=None, generic_auth_error=False):
        captured["path"] = path
        captured["bearer_token"] = bearer_token
        return {}

    monkeypatch.setattr(auth_controller, "_post_supabase_auth", fake_post)
    client.cookies.set("refresh_token", "refresh-123")

    response = client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer access-123"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "logged_out"}
    assert captured == {"path": "logout", "bearer_token": "access-123"}
    set_cookie = response.headers["set-cookie"]
    assert "refresh_token=" in set_cookie
    assert "auth_session=" in set_cookie
    assert "Max-Age=0" in set_cookie


def test_auth_routes_reject_cross_site_browser_requests(client, monkeypatch):
    def fake_call(path, payload):
        return {"access_token": "token-123"}

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    response = client.post(
        "/auth/login",
        headers={
            "Origin": "https://malicious.example",
            "Sec-Fetch-Site": "cross-site",
        },
        json={"email": "joao@example.com", "password": "123456"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Origem nao permitida."


def test_login_rate_limit_blocks_repeated_invalid_credentials(client, monkeypatch):
    limiter = auth_controller.AuthRateLimiter(
        max_attempts=2,
        window_seconds=60,
        base_block_seconds=30,
        max_block_seconds=30,
    )
    monkeypatch.setattr(auth_controller, "_auth_rate_limiter", limiter)

    def fake_call(path, payload):
        raise HTTPException(status_code=401, detail="Detalhe sensivel")

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    payload = {"email": "joao@example.com", "password": "123456"}
    first = client.post("/auth/login", json=payload)
    second = client.post("/auth/login", json=payload)
    third = client.post("/auth/login", json=payload)

    assert first.status_code == 401
    assert first.json()["detail"] == "Credenciais invalidas."
    assert second.status_code == 401
    assert third.status_code == 429


def _make_hs_token(payload: dict, secret: str = "test-secret", algorithm: str = "HS256") -> str:
    base_payload = {
        "iss": deps.SUPABASE_ISSUER,
        "aud": deps.SUPABASE_AUDIENCE,
        "exp": int(time.time()) + 300,
        **payload,
    }
    return jwt.encode(base_payload, secret, algorithm=algorithm)


def test_get_current_user_extracts_roles_from_jwt_metadata(monkeypatch):
    monkeypatch.setattr(deps, "SUPABASE_JWT_SECRET", "test-secret")
    token = _make_hs_token(
        {
            "sub": "user-1",
            "email": "joao@example.com",
            "app_metadata": {"roles": ["admin"]},
        }
    )

    user = deps.get_current_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )

    assert user.id == "user-1"
    assert user.email == "joao@example.com"
    assert user.roles == frozenset({"admin"})


def test_get_current_user_rejects_unsupported_jwt_algorithm(monkeypatch):
    monkeypatch.setattr(deps, "SUPABASE_JWT_SECRET", "test-secret")
    token = _make_hs_token({"sub": "user-1"}, algorithm="HS384")

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token invalido"


def test_get_current_user_rejects_expired_token(monkeypatch):
    monkeypatch.setattr(deps, "SUPABASE_JWT_SECRET", "test-secret")
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": deps.SUPABASE_ISSUER,
            "aud": deps.SUPABASE_AUDIENCE,
            "exp": int(time.time()) - 1,
        },
        "test-secret",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token expirado"


def test_get_current_user_rejects_token_without_sub(monkeypatch):
    monkeypatch.setattr(deps, "SUPABASE_JWT_SECRET", "test-secret")
    token = _make_hs_token({"email": "joao@example.com"})

    with pytest.raises(HTTPException) as exc_info:
        deps.get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User ID nao encontrado no token"


def test_require_permission_allows_default_user_dashboard_and_blocks_missing_role():
    dependency = deps.require_permission("dashboard:read_global")
    user = deps.AuthenticatedUser(
        id="user-1",
        email="joao@example.com",
        roles=frozenset({"user"}),
    )
    restricted = deps.AuthenticatedUser(
        id="user-2",
        email="maria@example.com",
        roles=frozenset({"restricted"}),
    )

    assert dependency(user) is user
    with pytest.raises(HTTPException) as exc_info:
        dependency(restricted)

    assert exc_info.value.status_code == 403
