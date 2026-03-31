from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from api.project_controller import router as project_router
from api.task_controller import router as task_router
from domain.exceptions import ValidationError

app = FastAPI(title="Registro de Projetos")


@app.exception_handler(ValidationError)
def domain_validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/app")


@app.get("/app/config", include_in_schema=False)
def frontend_config():
    return {
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", ""),
    }


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="app")

app.include_router(project_router)
app.include_router(task_router)
