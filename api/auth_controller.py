import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthPayload(BaseModel):
    email: str
    password: str


def _supabase_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase nao configurado no backend.",
        )

    return supabase_url, supabase_anon_key


def _call_supabase_auth(path: str, payload: AuthPayload) -> dict:
    supabase_url, supabase_anon_key = _supabase_credentials()
    endpoint = f"{supabase_url}/auth/v1/{path}"

    request = Request(
        endpoint,
        data=json.dumps(payload.model_dump()).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "apikey": supabase_anon_key,
            "Authorization": f"Bearer {supabase_anon_key}",
        },
    )

    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        detail = "Falha na autenticacao."
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            detail = (
                data.get("error_description")
                or data.get("msg")
                or data.get("error")
                or detail
            )
        raise HTTPException(status_code=exc.code, detail=detail) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Nao foi possivel conectar ao Supabase. "
                "Verifique internet, DNS e configuracao do projeto."
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro inesperado durante autenticacao.",
        ) from exc


@router.post("/login")
def login(payload: AuthPayload):
    return _call_supabase_auth("token?grant_type=password", payload)


@router.post("/signup")
def signup(payload: AuthPayload):
    return _call_supabase_auth("signup", payload)
