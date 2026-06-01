from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from api.project_controller import router as project_router
from api.routine_activity_controller import router as routine_activity_router
from api.task_controller import router as task_router
from api.auth_controller import router as auth_router
from api.dashboard_controller import router as dashboard_router
from domain.exceptions import ValidationError

app = FastAPI(title="Registro de Projetos")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "accelerometer=(), browsing-topics=(), camera=(), geolocation=(), "
        "gyroscope=(), interest-cohort=(), magnetometer=(), microphone=(), "
        "payment=(), usb=()"
    ),
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' https://cdn.plot.ly 'unsafe-eval'; "
        "script-src-attr 'none'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    ),
}
HSTS_HEADER = "max-age=31536000; includeSubDomains"


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _is_production_like_environment() -> bool:
    env = os.getenv("ENV", "").strip().lower()
    return (
        env in {"prod", "production"}
        or _truthy_env("RENDER")
        or bool(os.getenv("RENDER_SERVICE_ID"))
    )


def _first_header_value(value: str | None) -> str:
    return str(value or "").split(",", 1)[0].strip().lower()


def _apply_security_headers(response, *, include_hsts: bool):
    for header in ("Server", "X-Powered-By"):
        if header in response.headers:
            del response.headers[header]
    for header, value in SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    if include_hsts:
        response.headers.setdefault("Strict-Transport-Security", HSTS_HEADER)
    return response


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    forwarded_proto = _first_header_value(request.headers.get("x-forwarded-proto"))
    should_enforce_https = _is_production_like_environment()

    if should_enforce_https and forwarded_proto == "http":
        secure_url = request.url.replace(scheme="https")
        return _apply_security_headers(
            RedirectResponse(url=str(secure_url), status_code=308),
            include_hsts=True,
        )

    response = await call_next(request)
    return _apply_security_headers(response, include_hsts=should_enforce_https)


@app.exception_handler(ValidationError)
def domain_validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/app/login.html")


@app.get("/app", include_in_schema=False)
def app_redirect():
    return RedirectResponse(url="/app/login.html")


@app.get("/app/", include_in_schema=False)
def app_slash_redirect():
    return RedirectResponse(url="/app/login.html")


@app.get("/app/config", include_in_schema=False)
def frontend_config():
    return {
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", ""),
        "privacy_controller_name": os.getenv("PRIVACY_CONTROLLER_NAME", ""),
        "privacy_contact_email": os.getenv("PRIVACY_CONTACT_EMAIL", ""),
        "privacy_policy_version": os.getenv("PRIVACY_POLICY_VERSION", ""),
    }


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="app")

app.include_router(auth_router)
app.include_router(project_router)
app.include_router(task_router)
app.include_router(routine_activity_router)
app.include_router(dashboard_router)
