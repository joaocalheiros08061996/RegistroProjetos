from fastapi import HTTPException

import api.auth_controller as auth_controller


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


def test_signup_endpoint_maps_path_and_payload(client, monkeypatch):
    captured = {}

    def fake_call(path, payload):
        captured["path"] = path
        captured["email"] = payload.email
        return {"user": {"id": "user-1"}}

    monkeypatch.setattr(auth_controller, "_call_supabase_auth", fake_call)

    response = client.post(
        "/auth/signup",
        json={"email": "joao@example.com", "password": "123456"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "user-1"
    assert captured["path"] == "signup"
    assert captured["email"] == "joao@example.com"


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
