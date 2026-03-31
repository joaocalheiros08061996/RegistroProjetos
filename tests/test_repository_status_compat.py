from domain.enums import TaskStatus
from infra.database.repositories.project_repo import SupabaseProjectRepository
from infra.database.repositories.task_repo import SupabaseTaskRepository


def test_project_repo_coerces_legacy_task_status_values():
    assert SupabaseProjectRepository._coerce_task_status("Completed") == TaskStatus.COMPLETED
    assert SupabaseProjectRepository._coerce_task_status("In Progress") == TaskStatus.IN_PROGRESS
    assert SupabaseProjectRepository._coerce_task_status("Paused") == TaskStatus.PAUSED
    assert SupabaseProjectRepository._coerce_task_status("Planned") == TaskStatus.PLANNED


def test_task_repo_coerces_legacy_task_status_values():
    assert SupabaseTaskRepository._coerce_task_status("Completed") == TaskStatus.COMPLETED
    assert SupabaseTaskRepository._coerce_task_status("In Progress") == TaskStatus.IN_PROGRESS
    assert SupabaseTaskRepository._coerce_task_status("Paused") == TaskStatus.PAUSED
    assert SupabaseTaskRepository._coerce_task_status("Planned") == TaskStatus.PLANNED
