import json
import os
import time
from urllib.request import urlopen

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from application.services import ProjectService, RoutineActivityService, TaskService
from infra.database.repositories.project_repo import SupabaseProjectRepository
from infra.database.repositories.routine_activity_repo import (
    SupabaseRoutineActivityRepository,
)
from infra.database.repositories.task_repo import SupabaseTaskRepository

# ---------------------------------------------------------------------
# Auth / JWT (SEM MUDANÇA DE REGRA)
# ---------------------------------------------------------------------

ALGORITHM = "RS256"
security = HTTPBearer(auto_error=True)

SUPABASE_ISSUER = os.getenv(
    "SUPABASE_ISSUER",
    "https://enuafbjnbplfxtmrgpkp.supabase.co/auth/v1",
).rstrip("/")

SUPABASE_AUDIENCE = os.getenv("SUPABASE_AUDIENCE", "authenticated")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

JWKS_URL = f"{SUPABASE_ISSUER}/.well-known/jwks.json"
JWKS_CACHE_SECONDS = int(os.getenv("SUPABASE_JWKS_CACHE_SECONDS", "3600"))

_jwks_cache: dict[str, object] = {
    "expires_at": 0,
    "keys": [],
}

# ---------------------------------------------------------------------
# Repository factories
# ---------------------------------------------------------------------

def get_project_repository() -> SupabaseProjectRepository:
    return SupabaseProjectRepository()


def get_task_repository() -> SupabaseTaskRepository:
    return SupabaseTaskRepository()


def get_routine_activity_repository() -> SupabaseRoutineActivityRepository:
    return SupabaseRoutineActivityRepository()


# ---------------------------------------------------------------------
# Service factories (request-safe)
# ---------------------------------------------------------------------

def get_project_service(
    project_repo: SupabaseProjectRepository = Depends(get_project_repository),
    task_repo: SupabaseTaskRepository = Depends(get_task_repository),
) -> ProjectService:
    return ProjectService(project_repo, task_repo)


def get_task_service(
    project_repo: SupabaseProjectRepository = Depends(get_project_repository),
    task_repo: SupabaseTaskRepository = Depends(get_task_repository),
) -> TaskService:
    return TaskService(project_repo, task_repo)


def get_routine_activity_service(
    routine_repo: SupabaseRoutineActivityRepository = Depends(get_routine_activity_repository),
) -> RoutineActivityService:
    return RoutineActivityService(routine_repo)


# ---------------------------------------------------------------------
# JWKS helpers
# ---------------------------------------------------------------------

def _get_jwks_keys() -> list[dict]:
    now = int(time.time())
    expires_at = int(_jwks_cache.get("expires_at", 0))

    if now < expires_at and _jwks_cache["keys"]:
        return _jwks_cache["keys"]  # type: ignore[return-value]

    try:
        with urlopen(JWKS_URL, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            keys = data.get("keys", [])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Falha ao obter chaves de autenticacao",
        ) from exc

    if not keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nenhuma chave publica encontrada para autenticacao",
        )

    _jwks_cache["keys"] = keys
    _jwks_cache["expires_at"] = now + JWKS_CACHE_SECONDS
    return keys


def _decode_supabase_rs256(token: str) -> dict:
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise JWTError("Token sem kid")

    keys = _get_jwks_keys()
    key = next((item for item in keys if item.get("kid") == kid), None)
    if not key:
        raise JWTError("Chave publica nao encontrada para o kid informado")

    return jwt.decode(
        token,
        key=key,
        algorithms=[ALGORITHM],
        audience=SUPABASE_AUDIENCE,
        issuer=SUPABASE_ISSUER,
    )


def _decode_supabase_hs256(token: str) -> dict:
    if not SUPABASE_JWT_SECRET:
        raise JWTError("SUPABASE_JWT_SECRET nao configurado")

    return jwt.decode(
        token,
        key=SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience=SUPABASE_AUDIENCE,
        issuer=SUPABASE_ISSUER,
    )


def _decode_supabase_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    alg = str(header.get("alg", "")).upper()

    if alg == "HS256":
        return _decode_supabase_hs256(token)
    if alg == "RS256":
        return _decode_supabase_rs256(token)

    # fallback defensivo
    try:
        return _decode_supabase_rs256(token)
    except JWTError:
        return _decode_supabase_hs256(token)


# ---------------------------------------------------------------------
# Dependency: current user
# ---------------------------------------------------------------------

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials

    # Facilita testes locais
    if os.getenv("ENV", "").lower() == "test" and token.count(".") != 2:
        return token

    try:
        payload = _decode_supabase_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID nao encontrado no token",
        )

    return user_id
