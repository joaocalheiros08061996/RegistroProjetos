import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime

from application.services import ProjectService, TaskService
from infra.in_memory_repos import InMemoryProjectRepository, InMemoryTaskRepository
from domain.enums import ProcessClassification, ProjectType, Severity, Trend, Urgency
from domain.exceptions import ValidationError

USER_ID = "user-123"


@pytest.fixture
def services():
    project_repo = InMemoryProjectRepository()
    task_repo = InMemoryTaskRepository()

    project_service = ProjectService(project_repo, task_repo)
    task_service = TaskService(project_repo, task_repo)

    return project_service, task_service


# -------------------------
# ProjectService tests
# -------------------------

def test_create_project_service(services):
    project_service, _ = services

    project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Service",
        project_type=ProjectType.LAYOUT,
        process_classification=ProcessClassification.NEW,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    assert project.id is not None
    assert project.name == "Projeto Service"
    assert project.user_id == USER_ID
    assert project.process_classification == ProcessClassification.NEW
    assert project.task_count == 0


def test_list_projects_for_user(services):
    project_service, _ = services

    project_service.create_project(
        user_id=USER_ID,
        name="Projeto A",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
    )

    projects = project_service.list_projects_for_user(USER_ID)

    assert len(projects) == 1
    assert projects[0].name == "Projeto A"


def test_project_gut_score_and_priority_level(services):
    project_service, _ = services

    critical_project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Critico",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
        severity=Severity.CRITICAL,
        urgency=Urgency.IMMEDIATE,
        trend=Trend.RAPID,
    )
    low_project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Baixa Prioridade",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
        severity=Severity.NONE,
        urgency=Urgency.CAN_WAIT,
        trend=Trend.STABLE,
    )

    assert critical_project.gut_score == 125
    assert critical_project.priority_level == 1
    assert critical_project.priority_label == "Prioridade 1"

    assert low_project.gut_score == 1
    assert low_project.priority_level == 5
    assert low_project.priority_label == "Prioridade 5"


# -------------------------
# TaskService tests
# -------------------------

def test_add_task_to_project_service(services):
    project_service, task_service = services

    project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Tarefas",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    task = task_service.add_task(
        user_id=USER_ID,
        project_id=project.id,
        name="Tarefa A",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
        cost=500.0,
    )

    assert task.name == "Tarefa A"
    assert project.task_count == 1


def test_mark_task_completed_service(services):
    project_service, task_service = services

    project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Final",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    task_service.add_task(
        user_id=USER_ID,
        project_id=project.id,
        name="Finalizar",
        planned_start=datetime(2026, 1, 5),
        planned_end=datetime(2026, 1, 10),
    )

    task_service.complete_task(
        user_id=USER_ID,
        project_id=project.id,
        task_name="Finalizar",
    )

    metrics = project_service.get_project_metrics(project.id, USER_ID)

    assert "Finalizar" not in metrics["active_tasks"]


def test_add_task_to_nonexistent_project_raises_error(services):
    _, task_service = services

    with pytest.raises(ValidationError):
        task_service.add_task(
            user_id=USER_ID,
            project_id=999,
            name="Fantasma",
            planned_start=datetime(2026, 1, 1),
            planned_end=datetime(2026, 1, 2),
        )


def test_delete_task_service(services):
    project_service, task_service = services

    project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Delete Task",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    task_service.add_task(
        user_id=USER_ID,
        project_id=project.id,
        name="Remover tarefa",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )

    task_service.delete_task(project.id, USER_ID, "Remover tarefa")
    assert project_service.get_project(project.id, USER_ID).task_count == 0


def test_delete_project_service(services):
    project_service, _ = services

    project = project_service.create_project(
        user_id=USER_ID,
        name="Projeto Delete",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    project_service.delete_project(project.id, USER_ID)

    with pytest.raises(ValidationError):
        project_service.get_project(project.id, USER_ID)
