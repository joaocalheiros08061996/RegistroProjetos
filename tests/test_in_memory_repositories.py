import pytest
from datetime import datetime

from infra.in_memory_repos import (
    InMemoryProjectRepository,
    InMemoryTaskRepository,
)
from domain.entities import Project, Task, TimeEntry
from domain.enums import ProjectType, TaskStatus

USER_1 = "user-1"
USER_2 = "user-2"

# ============================
# Project Repository Tests
# ============================

def test_save_project_assigns_id_and_user():
    repo = InMemoryProjectRepository()

    project = Project(
        user_id=USER_1,
        name="Projeto Teste",
        project_type=ProjectType.LAYOUT,
        responsible_login="joao",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    project_id = repo.save(project)

    assert project_id == 1
    assert project.id == 1
    assert project.user_id == USER_1


def test_find_project_by_id_isolated_by_user():
    repo = InMemoryProjectRepository()

    project = Project(
        user_id=USER_1,
        name="Projeto A",
        project_type=ProjectType.LAYOUT,
        responsible_login="joao",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )

    project_id = repo.save(project)

    assert repo.find_by_id(project_id, USER_1) is project
    assert repo.find_by_id(project_id, USER_2) is None


def test_list_projects_by_user():
    repo = InMemoryProjectRepository()

    p1 = Project(
        user_id=USER_1,
        name="Projeto 1",
        project_type=ProjectType.LAYOUT,
        responsible_login="joao",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
    )

    p2 = Project(
        user_id=USER_2,
        name="Projeto 2",
        project_type=ProjectType.LAYOUT,
        responsible_login="maria",
        fte=1.0,
        planned_start=datetime(2026, 2, 1),
        planned_end=datetime(2026, 2, 10),
    )

    repo.save(p1)
    repo.save(p2)

    user1_projects = repo.list_by_user(USER_1)

    assert len(user1_projects) == 1
    assert user1_projects[0].name == "Projeto 1"


def test_project_summary_methods_return_aggregate_metrics():
    repo = InMemoryProjectRepository()

    project = Project(
        user_id=USER_1,
        name="Projeto Resumo",
        project_type=ProjectType.LAYOUT,
        responsible_login="joao",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 31),
    )
    repo.save(project)

    task_done = Task(
        name="Task Concluida",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )
    task_done._set_status(TaskStatus.COMPLETED)
    task_active = Task(
        name="Task Ativa",
        planned_start=datetime(2026, 1, 6),
        planned_end=datetime(2026, 1, 7),
    )
    project.add_task(task_done)
    project.add_task(task_active)

    summaries = repo.list_summary_by_user(USER_1)
    detail = repo.find_detail_summary(project.id, USER_1)

    assert summaries[0]["task_count"] == 2
    assert summaries[0]["percent_completed"] == 50.0
    assert detail["task_count"] == 2
    assert detail["active_tasks"] == ["Task Ativa"]


def test_delete_project_by_user():
    repo = InMemoryProjectRepository()

    project = Project(
        user_id=USER_1,
        name="Projeto Delete",
        project_type=ProjectType.LAYOUT,
        responsible_login="joao",
        fte=1.0,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 10),
    )
    project_id = repo.save(project)

    assert repo.delete(project_id, USER_1) is True
    assert repo.find_by_id(project_id, USER_1) is None
    assert repo.delete(project_id, USER_1) is False
    assert repo.delete(project_id, USER_2) is False

# ============================
# Task Repository Tests
# ============================

def test_save_task_assigns_id_and_project():
    repo = InMemoryTaskRepository()

    task = Task(
        name="Task Teste",
        description="Descrição salva em memória",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )

    task_id = repo.save(task, project_id=1, user_id=USER_1)

    assert task_id == 1
    assert task.id == 1
    assert repo.find_by_id(task_id, project_id=1, user_id=USER_1).description == (
        "Descrição salva em memória"
    )


def test_find_task_by_name_and_summary_methods():
    repo = InMemoryTaskRepository()

    task = Task(
        name="Task Summary",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )
    entry = TimeEntry(start=datetime(2026, 1, 2, 9, 0))
    entry.stop(datetime(2026, 1, 2, 10, 0))
    task._add_time_entry(entry)

    task_id = repo.save(task, project_id=1, user_id=USER_1)

    found = repo.find_by_name(project_id=1, user_id=USER_1, task_name="Task Summary")
    summary = repo.find_summary_by_name(
        project_id=1,
        user_id=USER_1,
        task_name="Task Summary",
    )

    assert found is task
    assert repo.find_id_by_name(1, USER_1, "Task Summary") == task_id
    assert summary["actual_seconds"] == 3600
    assert summary["time_entries_count"] == 1


def test_list_tasks_with_time_summary_can_filter_completed():
    repo = InMemoryTaskRepository()

    task_done = Task(
        name="Task Done",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )
    task_done._set_status(TaskStatus.COMPLETED)
    task_active = Task(
        name="Task Active",
        planned_start=datetime(2026, 1, 6),
        planned_end=datetime(2026, 1, 7),
    )
    repo.save(task_done, project_id=1, user_id=USER_1)
    repo.save(task_active, project_id=1, user_id=USER_1)

    all_tasks = repo.list_with_time_summary(1, USER_1, include_completed=True)
    active_tasks = repo.list_with_time_summary(1, USER_1, include_completed=False)

    assert [task["name"] for task in all_tasks] == ["Task Done", "Task Active"]
    assert [task["name"] for task in active_tasks] == ["Task Active"]


def test_append_time_entry_to_task():
    repo = InMemoryTaskRepository()

    task = Task(
        name="Task Tempo",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )

    task_id = repo.save(task, project_id=1, user_id=USER_1)

    entry = TimeEntry(start=datetime(2026, 1, 2, 9, 0))
    entry.stop(datetime(2026, 1, 2, 10, 0))

    repo.append_time_entry(
        task_id=task_id,
        project_id=1,
        user_id=USER_1,
        entry=entry,
    )

    found = repo.find_by_id(task_id, project_id=1, user_id=USER_1)

    assert len(found._time_entries) == 1
    assert found._time_entries[0].duration.total_seconds() == 3600


def test_delete_task_by_name():
    repo = InMemoryTaskRepository()

    task = Task(
        name="Task Delete",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )
    repo.save(task, project_id=1, user_id=USER_1)

    assert repo.delete_by_name(project_id=1, user_id=USER_1, task_name="Task Delete") is True
    assert repo.delete_by_name(project_id=1, user_id=USER_1, task_name="Task Delete") is False
    assert repo.delete_by_name(project_id=1, user_id=USER_2, task_name="Task Delete") is False


def test_delete_all_tasks_by_project():
    repo = InMemoryTaskRepository()

    task_a = Task(
        name="Task A",
        planned_start=datetime(2026, 1, 2),
        planned_end=datetime(2026, 1, 5),
    )
    task_b = Task(
        name="Task B",
        planned_start=datetime(2026, 1, 6),
        planned_end=datetime(2026, 1, 7),
    )
    repo.save(task_a, project_id=11, user_id=USER_1)
    repo.save(task_b, project_id=11, user_id=USER_1)

    deleted_count = repo.delete_by_project(project_id=11, user_id=USER_1)
    assert deleted_count == 2
    assert repo.find_by_id(task_a.id, project_id=11, user_id=USER_1) is None
    assert repo.delete_by_project(project_id=11, user_id=USER_1) == 0
