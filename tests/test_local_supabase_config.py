import base64
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
from dotenv import dotenv_values
from jose import JWTError, jwt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ENV_PATH = PROJECT_ROOT / ".env"


def _load_local_env() -> dict[str, str]:
    if not LOCAL_ENV_PATH.exists():
        pytest.skip("Local .env file not found.")

    values = {
        key: value
        for key, value in dotenv_values(LOCAL_ENV_PATH).items()
        if key and value
    }
    if not values.get("SUPABASE_URL"):
        pytest.skip("Local .env does not configure SUPABASE_URL.")

    return values


def _jwt_part(jwt_value: str, index: int) -> dict:
    parts = jwt_value.split(".")
    assert len(parts) == 3, "Supabase key must be a JWT with three parts."

    segment = parts[index]
    segment += "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(segment.encode("utf-8")))


def _project_ref_from_url(value: str) -> str | None:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    username = unquote(parsed.username or "")

    if host.endswith(".supabase.co"):
        parts = host.split(".")
        if parts[0] == "db" and len(parts) > 1:
            return parts[1]
        return parts[0]

    if username.startswith("postgres."):
        return username.split(".", 1)[1]

    return None


def test_local_supabase_issuer_matches_supabase_url():
    env = _load_local_env()
    supabase_url = env["SUPABASE_URL"].rstrip("/")
    expected_issuer = f"{supabase_url}/auth/v1"
    actual_issuer = env.get("SUPABASE_ISSUER", "").rstrip("/")

    assert actual_issuer == expected_issuer, (
        "SUPABASE_ISSUER must match SUPABASE_URL + '/auth/v1'. "
        "Otherwise login can succeed while protected API calls return 401."
    )


def test_local_supabase_project_references_are_consistent():
    env = _load_local_env()
    supabase_ref = _project_ref_from_url(env["SUPABASE_URL"])
    database_ref = _project_ref_from_url(env.get("DATABASE_URL", ""))
    anon_key_ref = _jwt_part(env.get("SUPABASE_ANON_KEY", ""), 1).get("ref")

    assert supabase_ref, "Could not detect project ref from SUPABASE_URL."
    assert database_ref == supabase_ref, (
        "DATABASE_URL and SUPABASE_URL point to different Supabase projects."
    )
    assert anon_key_ref == supabase_ref, (
        "SUPABASE_ANON_KEY and SUPABASE_URL point to different Supabase projects."
    )


def test_local_supabase_jwt_secret_matches_anon_key_when_hs256():
    env = _load_local_env()
    anon_key = env.get("SUPABASE_ANON_KEY", "")
    jwt_secret = env.get("SUPABASE_JWT_SECRET", "")
    anon_key_alg = _jwt_part(anon_key, 0).get("alg")

    if anon_key_alg != "HS256":
        pytest.skip("Anon key is not HS256; JWT secret signature check skipped.")

    assert jwt_secret, "SUPABASE_JWT_SECRET is required for HS256 tokens."

    try:
        jwt.decode(
            anon_key,
            jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise AssertionError(
            "SUPABASE_JWT_SECRET does not match SUPABASE_ANON_KEY."
        ) from exc
