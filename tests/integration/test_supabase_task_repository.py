import os
import uuid
from datetime import datetime

import pytest

from domain.entities import Project, Task, TimeEntry
from domain.enums import ProjectType
from infra.database.repositories.project_repo import SupabaseProjectRepository
from infra.database.repositories.task_repo import SupabaseTaskRepository

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Defina RUN_INTEGRATION_TESTS=1 para executar testes de integracao.",
    ),
]


def create_project_for_test(user_id: str) -> int:
    project_repo = SupabaseProjectRepository()

    project = Project(
        user_id=user_id,
        name="Projeto Integracao Tasks",
        project_type=ProjectType.LAYOUT,
        responsible_login="test",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
    )

    return project_repo.save(project)


def test_supabase_task_repository_save_and_load():
    task_repo = SupabaseTaskRepository()

    user_id = f"test-user-{uuid.uuid4()}"
    project_id = create_project_for_test(user_id)

    task = Task(
        name="Task Integracao",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
        cost=100.0,
    )

    task_id = task_repo.save(task, project_id, user_id)

    assert task_id is not None
    assert task.id == task_id

    loaded = task_repo.find_by_id(task_id, project_id, user_id)

    assert loaded is not None
    assert loaded.name == "Task Integracao"
    assert loaded.cost == 100.0
    assert loaded.percent_completed == 0.0


def test_supabase_task_time_entry():
    task_repo = SupabaseTaskRepository()

    user_id = f"test-user-{uuid.uuid4()}"
    project_id = create_project_for_test(user_id)

    task = Task(
        name="Task Tempo DB",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 5),
    )

    task_id = task_repo.save(task, project_id, user_id)

    entry = TimeEntry(start=datetime(2026, 1, 2, 9, 0))
    entry.stop(datetime(2026, 1, 2, 10, 30))

    task_repo.append_time_entry(task_id, project_id, user_id, entry)

    loaded = task_repo.find_by_id(task_id, project_id, user_id)

    assert loaded is not None
    assert loaded.actual_time.total_seconds() == 5400
