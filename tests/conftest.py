import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from api.deps import (
    get_project_service,
    get_routine_activity_service,
    get_task_service,
)
from api.main import app
from application.services import ProjectService, RoutineActivityService, TaskService
from infra.in_memory_repos import (
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


@pytest.fixture
def client():
    project_repo = InMemoryProjectRepository()
    task_repo = InMemoryTaskRepository()
    routine_repo = InMemoryRoutineActivityRepository()

    project_service = ProjectService(project_repo, task_repo)
    task_service = TaskService(project_repo, task_repo)
    routine_service = RoutineActivityService(routine_repo)

    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_task_service] = lambda: task_service
    app.dependency_overrides[get_routine_activity_service] = lambda: routine_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
