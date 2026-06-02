from datetime import datetime

import pytest

from domain.entities import Project, Task
from domain.enums import ProjectType, TaskStatus
from domain.exceptions import (
    TaskAlreadyCompletedError,
    TaskAlreadyStartedError,
    TaskNotStartedError,
    ValidationError,
)

USER_ID = "user-123"


@pytest.fixture
def project():
    return Project(
        user_id=USER_ID,
        name="Projeto Base",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )


def test_create_project():
    created = Project(
        user_id=USER_ID,
        name="Projeto Teste",
        project_type=ProjectType.LAYOUT,
        responsible_login="user1",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
    )

    assert created.name == "Projeto Teste"
    assert created.task_count == 0
    assert created.user_id == USER_ID


def test_project_rejects_invalid_fte():
    with pytest.raises(ValidationError):
        Project(
            user_id=USER_ID,
            name="Projeto Invalido",
            project_type=ProjectType.LAYOUT,
            responsible_login="user1",
            fte=0.0,
            planned_start=datetime(2026, 1, 1),
            planned_end=datetime(2026, 1, 31),
        )


def test_project_rejects_fractional_fte():
    with pytest.raises(ValidationError, match="FTE deve ser um numero inteiro"):
        Project(
            user_id=USER_ID,
            name="Projeto FTE Fracionado",
            project_type=ProjectType.LAYOUT,
            responsible_login="user1",
            fte=1.2,
            planned_start=datetime(2026, 1, 1),
            planned_end=datetime(2026, 1, 31),
        )


def test_project_rejects_end_before_start():
    with pytest.raises(ValidationError):
        Project(
            user_id=USER_ID,
            name="Projeto Invalido",
            project_type=ProjectType.LAYOUT,
            responsible_login="user1",
            fte=1.0,
            planned_start=datetime(2026, 1, 31),
            planned_end=datetime(2026, 1, 1),
        )


def test_add_task_increments_task_count(project):
    task = project.start_new_task(
        name="Tarefa A",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 3),
    )

    assert project.task_count == 1
    assert task.name == "Tarefa A"


def test_cannot_add_duplicate_task_names(project):
    project.start_new_task(
        name="Tarefa A",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 3),
    )

    with pytest.raises(ValidationError):
        project.start_new_task(
            name="Tarefa A",
            planned_start=datetime(2026, 1, 4),
            planned_end=datetime(2026, 1, 5),
        )


def test_task_start_and_stop_updates_status_and_duration():
    task = Task(
        name="Tarefa Tempo",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )

    start_at = datetime(2026, 1, 1, 9, 0, 0)
    stop_at = datetime(2026, 1, 1, 10, 30, 0)

    task.start(when=start_at)
    duration = task.stop(when=stop_at)

    assert task.status == TaskStatus.PAUSED
    assert duration.total_seconds() == 5400
    assert task.actual_time.total_seconds() == 5400


def test_task_cannot_start_twice():
    task = Task(
        name="Tarefa Start",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )
    task.start(when=datetime(2026, 1, 1, 9, 0, 0))

    with pytest.raises(TaskAlreadyStartedError):
        task.start(when=datetime(2026, 1, 1, 9, 15, 0))


def test_task_stop_without_start_raises_error():
    task = Task(
        name="Tarefa Stop",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )

    with pytest.raises(TaskNotStartedError):
        task.stop(when=datetime(2026, 1, 1, 10, 0, 0))


def test_task_mark_completed_changes_status_and_percent():
    task = Task(
        name="Tarefa Concluir",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )

    task.mark_completed()

    assert task.status == TaskStatus.COMPLETED
    assert task.percent_completed == 100.0
    assert task.is_completed is True


def test_task_cannot_be_completed_twice():
    task = Task(
        name="Tarefa X",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )

    task.mark_completed()

    with pytest.raises(TaskAlreadyCompletedError):
        task.mark_completed()


def test_project_percent_completed(project):
    task_1 = project.start_new_task(
        name="Tarefa 1",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 3),
    )
    project.start_new_task(
        name="Tarefa 2",
        planned_start=datetime(2026, 1, 4),
        planned_end=datetime(2026, 1, 5),
    )

    task_1.mark_completed()

    assert project.percent_completed == 50.0


def test_project_lists_active_and_completed_tasks(project):
    done = project.start_new_task(
        name="Concluida",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )
    open_task = project.start_new_task(
        name="Em aberto",
        planned_start=datetime(2026, 1, 3),
        planned_end=datetime(2026, 1, 4),
    )
    done.mark_completed()

    active_names = [task.name for task in project.active_tasks()]
    completed_names = [task.name for task in project.completed_tasks()]

    assert active_names == [open_task.name]
    assert completed_names == [done.name]


def test_project_actual_days_uses_task_entries(project):
    task = project.start_new_task(
        name="Tempo",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 2),
    )
    task.add_manual_entry(
        start=datetime(2026, 1, 1, 8, 0, 0),
        end=datetime(2026, 1, 1, 20, 0, 0),
    )

    assert project.actual_days() == 12.0 / 24.0
