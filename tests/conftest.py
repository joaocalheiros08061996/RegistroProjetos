import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from api.deps import (
    get_dashboard_service,
    get_project_service,
    get_routine_activity_service,
    get_task_service,
)
from api.main import app
from application.services import (
    DashboardService,
    ProjectService,
    RoutineActivityService,
    TaskService,
)
from infra.in_memory_repos import (
    InMemoryDashboardRepository,
    InMemoryProjectRepository,
    InMemoryRoutineActivityRepository,
    InMemoryTaskRepository,
)


def pytest_sessionstart(session):
    load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    os.environ["ENV"] = "test"
    os.environ["SUPABASE_JWT_SECRET"] = "test-secret"
    os.environ["PRIVACY_POLICY_VERSION"] = "2026-06-01"
    os.environ["PRIVACY_AUDIT_HASH_SECRET"] = "privacy-audit-test-secret"
    os.environ["PRIVACY_CONTROLLER_NAME"] = "Controlador de Teste"
    os.environ["PRIVACY_CONTACT_EMAIL"] = "privacidade@example.com"


@pytest.fixture
def client():
    project_repo = InMemoryProjectRepository()
    task_repo = InMemoryTaskRepository()
    routine_repo = InMemoryRoutineActivityRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo, routine_repo)

    project_service = ProjectService(project_repo, task_repo)
    task_service = TaskService(project_repo, task_repo)
    routine_service = RoutineActivityService(routine_repo)
    dashboard_service = DashboardService(dashboard_repo)

    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_task_service] = lambda: task_service
    app.dependency_overrides[get_routine_activity_service] = lambda: routine_service
    app.dependency_overrides[get_dashboard_service] = lambda: dashboard_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
