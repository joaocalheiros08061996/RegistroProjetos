from datetime import datetime
import time
from typing import List

from application.performance import log_perf
from domain.task import Task
from domain.enums import TaskStatus
from domain.exceptions import ValidationError
from domain.repositories import IProjectRepository, ITaskRepository


class TaskService:
    def __init__(self, project_repo: IProjectRepository, task_repo: ITaskRepository):
        self.project_repo = project_repo
        self.task_repo = task_repo

    def list_tasks(self, project_id: int, user_id: str) -> List[Task]:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")
        return project.list_tasks()

    def get_task(self, project_id: int, user_id: str, task_name: str) -> Task:
        task = self.task_repo.find_by_name(project_id, user_id, task_name)
        if task:
            return task
        raise ValidationError("Tarefa não encontrada.")

    def get_task_summary(
        self,
        project_id: int,
        user_id: str,
        task_name: str,
    ) -> dict:
        started_at = time.perf_counter()
        task = self.task_repo.find_summary_by_name(project_id, user_id, task_name)
        if not task:
            raise ValidationError("Tarefa não encontrada.")

        log_perf(
            "tasks.find_summary",
            started_at,
            project_id=project_id,
            task_name=task_name,
        )
        return task

    def add_task(
        self,
        *,
        project_id: int,
        user_id: str,
        name: str,
        planned_start: datetime,
        planned_end: datetime,
        cost: float = 0.0,
        description: str = "",
    ) -> Task:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")

        task = project.start_new_task(
            name=name,
            planned_start=planned_start,
            planned_end=planned_end,
            cost=cost,
            description=description,
        )

        self.task_repo.save(task, project_id, user_id)
        return task

    def start_task(self, project_id: int, user_id: str, task_name: str) -> None:
        task = self.get_task(project_id, user_id, task_name)

        now = datetime.utcnow()
        task.start(now)

        if task.id is None:
            raise ValidationError("Task sem ID persistido.")

        self.task_repo.update_status(task.id, task.status.value)
        self.task_repo.start_time_entry(task.id, now)

    def stop_task(self, project_id: int, user_id: str, task_name: str) -> float:
        task = self.get_task(project_id, user_id, task_name)

        now = datetime.utcnow()
        duration = task.stop(now)

        if task.id is None:
            raise ValidationError("Task sem ID persistido.")

        self.task_repo.update_status(task.id, task.status.value)
        self.task_repo.close_open_time_entry(task.id, now)

        return round(duration.total_seconds(), 2)

    def complete_task(self, project_id: int, user_id: str, task_name: str) -> None:
        task = self.get_task(project_id, user_id, task_name)

        task.mark_completed()

        if task.id is None:
            raise ValidationError("Task sem ID persistido.")

        self.task_repo.update_status(task.id, TaskStatus.COMPLETED.value)

        # garante que não exista entrada aberta
        self.task_repo.close_open_time_entry(task.id, datetime.utcnow())

    def delete_task(self, project_id: int, user_id: str, task_name: str) -> None:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")

        self.get_task(project_id, user_id, task_name)
        deleted = self.task_repo.delete_by_name(project_id, user_id, task_name)
        if not deleted:
            raise ValidationError("Tarefa não encontrada.")

        project.remove_task(task_name)

    def get_time_entries(self, project_id: int, user_id: str, task_name: str):
        started_at = time.perf_counter()
        task_id = self.task_repo.find_id_by_name(project_id, user_id, task_name)
        if task_id is None:
            raise ValidationError("Tarefa não encontrada.")

        entries = self.task_repo.list_time_entries(task_id)
        log_perf(
            "tasks.time_entries",
            started_at,
            project_id=project_id,
            task_name=task_name,
            entry_count=len(entries),
        )
        return entries
