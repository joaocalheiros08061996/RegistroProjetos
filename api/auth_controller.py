import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from fastapi import (
    APIRouter,
    Cookie,
    Header,
    HTTPException,
    Request as FastAPIRequest,
    Response,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from infra.database.repositories.privacy_acknowledgement_repo import (
    SupabasePrivacyAcknowledgementRepository,
)
from infra.security.privacy_audit import (
    PrivacyAuditConfigError,
    configured_audit_hash_secret,
    configured_policy_version,
    privacy_audit_hash,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
SESSION_COOKIE_NAME = "auth_session"
REFRESH_COOKIE_PATH = "/auth"
REFRESH_COOKIE_MAX_AGE_SECONDS = int(
    os.getenv("AUTH_REFRESH_COOKIE_MAX_AGE_SECONDS", str(30 * 24 * 60 * 60))
)
AUTH_SESSION_IDLE_TIMEOUT_SECONDS = int(
    os.getenv("AUTH_SESSION_IDLE_TIMEOUT_SECONDS", str(8 * 60 * 60))
)
AUTH_SESSION_ABSOLUTE_TIMEOUT_SECONDS = int(
    os.getenv("AUTH_SESSION_ABSOLUTE_TIMEOUT_SECONDS", str(30 * 24 * 60 * 60))
)
AUTH_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("AUTH_RATE_LIMIT_MAX_ATTEMPTS", "5"))
AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60"))
AUTH_RATE_LIMIT_BASE_BLOCK_SECONDS = int(
    os.getenv("AUTH_RATE_LIMIT_BASE_BLOCK_SECONDS", "60")
)
AUTH_RATE_LIMIT_MAX_BLOCK_SECONDS = int(
    os.getenv("AUTH_RATE_LIMIT_MAX_BLOCK_SECONDS", "900")
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = str(value or "").strip().lower()
        if not _EMAIL_RE.match(email):
            raise ValueError("Email invalido.")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        password = str(value or "")
        if len(password) < 6:
            raise ValueError("Senha deve ter pelo menos 6 caracteres.")
        return password


class SignupPayload(AuthPayload):
    privacy_notice_acknowledged: Literal[True]


@dataclass
class _RateLimitState:
    attempts: int = 0
    first_attempt_at: float = 0.0
    blocked_until: float = 0.0
    blocks: int = 0


@dataclass(frozen=True)
class _AuthSession:
    session_id: str
    issued_at: int
    last_seen_at: int
    refresh_token_hash: str


class AuthRateLimiter:
    def __init__(
        self,
        *,
        max_attempts: int,
        window_seconds: int,
        base_block_seconds: int,
        max_block_seconds: int,
    ) -> None:
        self.max_attempts = max(1, max_attempts)
        self.window_seconds = max(1, window_seconds)
        self.base_block_seconds = max(1, base_block_seconds)
        self.max_block_seconds = max(self.base_block_seconds, max_block_seconds)
        self._lock = threading.Lock()
        self._states: dict[str, _RateLimitState] = {}

    def check(self, key: str) -> None:
        now = time.time()
        with self._lock:
            state = self._states.get(key)
            if not state:
                return

            if state.blocked_until > now:
                retry_after = max(1, int(state.blocked_until - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Muitas tentativas. Tente novamente mais tarde.",
                    headers={"Retry-After": str(retry_after)},
                )

            if state.first_attempt_at and now - state.first_attempt_at > self.window_seconds:
                state.attempts = 0
                state.first_attempt_at = 0.0

    def register_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            state = self._states.setdefault(key, _RateLimitState())

            if not state.first_attempt_at or now - state.first_attempt_at > self.window_seconds:
                state.attempts = 0
                state.first_attempt_at = now

            state.attempts += 1
            if state.attempts < self.max_attempts:
                return

            state.blocks += 1
            block_seconds = min(
                self.max_block_seconds,
                self.base_block_seconds * (2 ** max(0, state.blocks - 1)),
            )
            state.blocked_until = now + block_seconds
            state.attempts = 0
            state.first_attempt_at = now

    def register_success(self, key: str) -> None:
        with self._lock:
            self._states.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._states.clear()


_auth_rate_limiter = AuthRateLimiter(
    max_attempts=AUTH_RATE_LIMIT_MAX_ATTEMPTS,
    window_seconds=AUTH_RATE_LIMIT_WINDOW_SECONDS,
    base_block_seconds=AUTH_RATE_LIMIT_BASE_BLOCK_SECONDS,
    max_block_seconds=AUTH_RATE_LIMIT_MAX_BLOCK_SECONDS,
)


def _supabase_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")

    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase nao configurado no backend.",
        )

    return supabase_url, supabase_anon_key


def _post_supabase_auth(
    path: str,
    payload: dict,
    *,
    bearer_token: str | None = None,
    generic_auth_error: bool = False,
) -> dict:
    supabase_url, supabase_anon_key = _supabase_credentials()
    endpoint = f"{supabase_url}/auth/v1/{path}"

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "apikey": supabase_anon_key,
            "Authorization": f"Bearer {bearer_token or supabase_anon_key}",
        },
    )

    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        if generic_auth_error and exc.code in (400, 401, 422):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas.",
            ) from exc

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


def _call_supabase_auth(path: str, payload: AuthPayload) -> dict:
    return _post_supabase_auth(
        path,
        {
            "email": payload.email,
            "password": payload.password,
        },
    )


def _is_secure_cookie() -> bool:
    override = os.getenv("AUTH_COOKIE_SECURE")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}

    return os.getenv("ENV", "").lower() not in {"test", "local", "dev", "development"}


def _session_signing_secret() -> bytes:
    secret = (
        os.getenv("AUTH_SESSION_SIGNING_SECRET", "").strip()
        or os.getenv("SUPABASE_JWT_SECRET", "").strip()
    )
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chave de sessao nao configurada no backend.",
        )
    return secret.encode("utf-8")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode_session(session: _AuthSession) -> str:
    payload = json.dumps(
        {
            "session_id": session.session_id,
            "issued_at": session.issued_at,
            "last_seen_at": session.last_seen_at,
            "refresh_token_hash": session.refresh_token_hash,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        _session_signing_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"v1.{encoded_payload}.{signature}"


def _decode_session(value: str) -> _AuthSession:
    try:
        version, encoded_payload, signature = value.split(".", 2)
        if version != "v1":
            raise ValueError("versao invalida")
        expected_signature = hmac.new(
            _session_signing_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("assinatura invalida")
        padding = "=" * (-len(encoded_payload) % 4)
        payload = json.loads(
            base64.urlsafe_b64decode(encoded_payload + padding).decode("utf-8")
        )
        return _AuthSession(
            session_id=str(payload["session_id"]),
            issued_at=int(payload["issued_at"]),
            last_seen_at=int(payload["last_seen_at"]),
            refresh_token_hash=str(payload["refresh_token_hash"]),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao de refresh invalida.",
        ) from exc


def _validate_refresh_session(refresh_token: str, session_cookie: str) -> _AuthSession:
    session = _decode_session(session_cookie)
    now = int(time.time())
    if not hmac.compare_digest(session.refresh_token_hash, _token_hash(refresh_token)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao de refresh invalida.",
        )
    if now - session.last_seen_at > AUTH_SESSION_IDLE_TIMEOUT_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao expirada por inatividade.",
        )
    if now - session.issued_at > AUTH_SESSION_ABSOLUTE_TIMEOUT_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao expirada.",
        )
    return session


def _extract_refresh_token(data: dict) -> str | None:
    refresh_token = data.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        return refresh_token

    session = data.get("session")
    if isinstance(session, dict):
        refresh_token = session.get("refresh_token")
        if isinstance(refresh_token, str) and refresh_token:
            return refresh_token

    return None


def _set_refresh_cookie(response: Response, data: dict) -> None:
    refresh_token = _extract_refresh_token(data)
    if not refresh_token:
        return

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=_is_secure_cookie(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _set_session_cookie(
    response: Response,
    refresh_token: str,
    *,
    previous_session: _AuthSession | None = None,
) -> None:
    now = int(time.time())
    issued_at = previous_session.issued_at if previous_session else now
    remaining_absolute_seconds = max(
        1,
        AUTH_SESSION_ABSOLUTE_TIMEOUT_SECONDS - (now - issued_at),
    )
    cookie_max_age = min(
        REFRESH_COOKIE_MAX_AGE_SECONDS,
        AUTH_SESSION_IDLE_TIMEOUT_SECONDS,
        remaining_absolute_seconds,
    )
    session = _AuthSession(
        session_id=secrets.token_urlsafe(24),
        issued_at=issued_at,
        last_seen_at=now,
        refresh_token_hash=_token_hash(refresh_token),
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=_encode_session(session),
        max_age=cookie_max_age,
        httponly=True,
        secure=_is_secure_cookie(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _set_auth_cookies(
    response: Response,
    data: dict,
    *,
    previous_session: _AuthSession | None = None,
    fallback_refresh_token: str | None = None,
) -> None:
    refresh_token = _extract_refresh_token(data) or fallback_refresh_token
    if not refresh_token:
        return
    _set_refresh_cookie(response, {"refresh_token": refresh_token})
    _set_session_cookie(response, refresh_token, previous_session=previous_session)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=_is_secure_cookie(),
        samesite="lax",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        secure=_is_secure_cookie(),
        samesite="lax",
    )


def _clear_auth_cookies(response: Response) -> None:
    _clear_refresh_cookie(response)
    _clear_session_cookie(response)


def _refresh_error_response(detail: str) -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": detail},
    )
    _clear_auth_cookies(response)
    return response


def _public_auth_response(data: dict) -> dict:
    sanitized = dict(data)
    sanitized.pop("refresh_token", None)

    session = sanitized.get("session")
    if isinstance(session, dict):
        safe_session = dict(session)
        safe_session.pop("refresh_token", None)
        sanitized["session"] = safe_session

    return sanitized


def _client_ip(request: FastAPIRequest) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _normalize_origin(value: str) -> str:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def _allowed_auth_origins(request: FastAPIRequest) -> set[str]:
    configured = os.getenv("APP_ALLOWED_ORIGINS", "")
    origins = {
        normalized
        for value in configured.split(",")
        if (normalized := _normalize_origin(value))
    }
    app_base_url = _normalize_origin(os.getenv("APP_BASE_URL", ""))
    request_base_url = _normalize_origin(str(request.base_url))
    if app_base_url:
        origins.add(app_base_url)
    if request_base_url:
        origins.add(request_base_url)
    return origins


def _validate_auth_origin(request: FastAPIRequest) -> None:
    fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
    if fetch_site == "cross-site":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origem nao permitida.",
        )

    source = request.headers.get("origin") or request.headers.get("referer")
    if not source:
        return

    normalized_source = _normalize_origin(source)
    if not normalized_source or normalized_source not in _allowed_auth_origins(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origem nao permitida.",
        )


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _privacy_policy_version() -> str:
    try:
        return configured_policy_version()
    except PrivacyAuditConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Versao do aviso de privacidade nao configurada.",
        ) from exc


def _privacy_audit_hash(value: str) -> str:
    try:
        return privacy_audit_hash(value)
    except PrivacyAuditConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chave de auditoria de privacidade nao configurada.",
        ) from exc


def _signup_user_id(data: dict) -> str:
    user = data.get("user")
    if isinstance(user, dict) and user.get("id"):
        return str(user["id"])

    session = data.get("session")
    if isinstance(session, dict):
        user = session.get("user")
        if isinstance(user, dict) and user.get("id"):
            return str(user["id"])

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Cadastro criado sem identificador de usuario para auditoria.",
    )


def _record_signup_privacy_acknowledgement(
    *,
    user_id: str,
    email: str,
    client_ip: str,
    policy_version: str,
) -> None:
    try:
        SupabasePrivacyAcknowledgementRepository().record_signup_acknowledgement(
            user_id=user_id,
            policy_version=policy_version,
            email_hash=_privacy_audit_hash(email),
            ip_hash=_privacy_audit_hash(client_ip),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel registrar a ciencia do aviso de privacidade.",
        ) from exc


def _rate_limit_key(request: FastAPIRequest, action: str, identifier: str) -> str:
    normalized_identifier = str(identifier or "").strip().lower() or "unknown"
    return f"{action}:{_client_ip(request)}:{normalized_identifier}"


def _register_auth_failure(exc: HTTPException, key: str) -> None:
    if exc.status_code in (
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        422,
    ):
        _auth_rate_limiter.register_failure(key)


def _bearer_from_authorization(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@router.post("/login")
def login(payload: AuthPayload, request: FastAPIRequest, response: Response):
    _validate_auth_origin(request)
    _session_signing_secret()
    key = _rate_limit_key(request, "login", payload.email)
    _auth_rate_limiter.check(key)

    try:
        data = _call_supabase_auth("token?grant_type=password", payload)
    except HTTPException as exc:
        _register_auth_failure(exc, key)
        if exc.status_code in (400, 401, 422):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas.",
            ) from exc
        raise

    _auth_rate_limiter.register_success(key)
    _set_auth_cookies(response, data)
    return _public_auth_response(data)


@router.post("/signup")
def signup(payload: SignupPayload, request: FastAPIRequest, response: Response):
    _validate_auth_origin(request)
    _session_signing_secret()
    policy_version = _privacy_policy_version()
    try:
        configured_audit_hash_secret()
    except PrivacyAuditConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chave de auditoria de privacidade nao configurada.",
        ) from exc
    key = _rate_limit_key(request, "signup", payload.email)
    _auth_rate_limiter.check(key)

    try:
        data = _call_supabase_auth("signup", payload)
    except HTTPException as exc:
        _register_auth_failure(exc, key)
        raise

    _record_signup_privacy_acknowledgement(
        user_id=_signup_user_id(data),
        email=payload.email,
        client_ip=_client_ip(request),
        policy_version=policy_version,
    )
    _auth_rate_limiter.register_success(key)
    _set_auth_cookies(response, data)
    return _public_auth_response(data)


@router.post("/refresh")
def refresh_session(
    request: FastAPIRequest,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    auth_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    _validate_auth_origin(request)
    if not refresh_token:
        return _refresh_error_response("Refresh token ausente.")
    if not auth_session:
        return _refresh_error_response("Sessao de refresh ausente.")

    try:
        parsed_session = _validate_refresh_session(refresh_token, auth_session)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return _refresh_error_response(str(exc.detail))
        raise

    key = _rate_limit_key(request, "refresh", _fingerprint(refresh_token))
    _auth_rate_limiter.check(key)

    try:
        data = _post_supabase_auth(
            "token?grant_type=refresh_token",
            {"refresh_token": refresh_token},
            generic_auth_error=True,
        )
    except HTTPException as exc:
        _register_auth_failure(exc, key)
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return _refresh_error_response(str(exc.detail))
        raise

    _auth_rate_limiter.register_success(key)
    _set_auth_cookies(
        response,
        data,
        previous_session=parsed_session,
        fallback_refresh_token=refresh_token,
    )
    return _public_auth_response(data)


@router.post("/logout")
def logout(
    request: FastAPIRequest,
    response: Response,
    authorization: str | None = Header(default=None),
):
    _validate_auth_origin(request)
    access_token = _bearer_from_authorization(authorization)
    if access_token:
        try:
            _post_supabase_auth("logout", {}, bearer_token=access_token)
        except HTTPException:
            pass

    _clear_auth_cookies(response)
    return {"status": "logged_out"}
