import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.request import urlopen

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from application.services import (
    DashboardService,
    ProjectService,
    RoutineActivityService,
    TaskService,
)
from infra.database.repositories.dashboard_repo import SupabaseDashboardRepository
from infra.database.repositories.project_repo import SupabaseProjectRepository
from infra.database.repositories.routine_activity_repo import (
    SupabaseRoutineActivityRepository,
)
from infra.database.repositories.task_repo import SupabaseTaskRepository

# ---------------------------------------------------------------------
# Auth / JWT / RBAC
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    roles: frozenset[str] = frozenset({"user"})


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

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "user": frozenset(
        {
            "projects:read_own",
            "projects:write_own",
            "tasks:read_own",
            "tasks:write_own",
            "routine:read_own",
            "routine:write_own",
            "dashboard:read_global",
        }
    ),
    "admin": frozenset({"*"}),
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


def get_dashboard_repository() -> SupabaseDashboardRepository:
    return SupabaseDashboardRepository()


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


def get_dashboard_service(
    dashboard_repo: SupabaseDashboardRepository = Depends(get_dashboard_repository),
) -> DashboardService:
    return DashboardService(dashboard_repo)


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
        algorithms=["RS256"],
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

    raise JWTError("Algoritmo de token nao permitido")


# ---------------------------------------------------------------------
# Dependency: current user
# ---------------------------------------------------------------------

def _test_email_from_token(token: str) -> str:
    return token.strip() if "@" in token else f"{token.strip()}@test.local"


def _extract_email(payload: dict, fallback: str) -> str:
    email = str(payload.get("email") or "").strip()
    if email:
        return email

    metadata = payload.get("user_metadata")
    if isinstance(metadata, dict):
        email = str(metadata.get("email") or "").strip()
        if email:
            return email

    app_metadata = payload.get("app_metadata")
    if isinstance(app_metadata, dict):
        email = str(app_metadata.get("email") or "").strip()
        if email:
            return email

    return fallback


def _roles_from_value(value: object) -> set[str]:
    roles: set[str] = set()

    if isinstance(value, str):
        candidates = value.replace(",", " ").split()
    elif isinstance(value, (list, tuple, set, frozenset)):
        candidates = value
    else:
        candidates = []

    for candidate in candidates:
        role = str(candidate or "").strip().lower()
        if role:
            roles.add(role)

    return roles


def _extract_roles(payload: dict) -> frozenset[str]:
    roles: set[str] = set()

    app_metadata = payload.get("app_metadata")
    if isinstance(app_metadata, dict):
        roles.update(_roles_from_value(app_metadata.get("roles")))
        roles.update(_roles_from_value(app_metadata.get("role")))

    roles.update(_roles_from_value(payload.get("roles")))
    roles.update(_roles_from_value(payload.get("role")))

    # Supabase costuma usar role=authenticated. Para a aplicacao, isso equivale
    # ao papel base "user" quando nao ha papel de negocio mais especifico.
    if not roles or roles == {"authenticated"}:
        roles = {"user"}
    else:
        roles.discard("authenticated")
        roles.discard("anon")

    return frozenset(roles or {"user"})


def _validate_required_claims(payload: dict) -> None:
    for claim in ("iss", "aud", "exp"):
        if payload.get(claim) in (None, ""):
            raise JWTError(f"Token sem claim obrigatoria: {claim}")


def _has_permission(user: AuthenticatedUser, permission: str) -> bool:
    for role in user.roles:
        permissions = ROLE_PERMISSIONS.get(role, frozenset())
        if "*" in permissions or permission in permissions:
            return True
    return False


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AuthenticatedUser:
    token = credentials.credentials

    # Facilita testes locais
    if os.getenv("ENV", "").lower() == "test" and token.count(".") != 2:
        return AuthenticatedUser(
            id=token,
            email=_test_email_from_token(token),
            roles=frozenset({"user"}),
        )

    try:
        payload = _decode_supabase_token(token)
        _validate_required_claims(payload)
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

    user_id = str(user_id)
    email = _extract_email(payload, fallback=user_id)

    return AuthenticatedUser(
        id=user_id,
        email=email,
        roles=_extract_roles(payload),
    )


def get_current_user_id(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    return current_user.id


def require_permission(permission: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    def _dependency(
        current_user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        if not _has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissao insuficiente",
            )
        return current_user

    return _dependency
