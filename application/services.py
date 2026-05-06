# services.py

from datetime import datetime, timezone
from typing import Dict, List, Optional

from domain.entities import Project, Task
from domain.enums import (
    MethodClarity,
    ObjectiveClarity,
    ProjectType,
    Severity,
    TaskStatus,
    Trend,
    Urgency,
)
from domain.exceptions import ValidationError
from domain.repositories import (
    IProjectRepository,
    IRoutineActivityRepository,
    ITaskRepository,
)
from domain.routine_activity import RoutineActivity


# ============================================================
# PROJECT SERVICE
# ============================================================

class ProjectService:
    def __init__(self, project_repo: IProjectRepository, task_repo: ITaskRepository):
        self.project_repo = project_repo
        self.task_repo = task_repo

    def create_project(
        self,
        *,
        user_id: str,
        name: str,
        project_type: ProjectType,
        responsible_login: str,
        fte: float,
        planned_start: datetime,
        planned_end: datetime,
        severity: Severity = Severity.NONE,
        urgency: Urgency = Urgency.CAN_WAIT,
        trend: Trend = Trend.STABLE,
        objective_clarity: ObjectiveClarity = ObjectiveClarity.FULLY_DEFINED,
        method_clarity: MethodClarity = MethodClarity.FULLY_DEFINED,
        estimated_cost: float = 0.0,
    ) -> Project:
        project = Project(
            user_id=user_id,
            name=name,
            project_type=project_type,
            responsible_login=responsible_login,
            fte=fte,
            planned_start=planned_start,
            planned_end=planned_end,
            severity=severity,
            urgency=urgency,
            trend=trend,
            objective_clarity=objective_clarity,
            method_clarity=method_clarity,
            estimated_cost=estimated_cost,
        )

        self.project_repo.save(project)
        return project

    def list_projects_for_user(self, user_id: str) -> List[Project]:
        return self.project_repo.list_by_user(user_id)

    def get_project(self, project_id: int, user_id: str) -> Project:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")
        return project

    def get_project_metrics(self, project_id: int, user_id: str) -> Dict:
        project = self.get_project(project_id, user_id)

        return {
            "percent_completed": project.percent_completed,
            "actual_days": project.actual_days(),
            "task_count": project.task_count,
            "active_tasks": [t.name for t in project.active_tasks()],
        }

    def delete_project(self, project_id: int, user_id: str) -> None:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")

        self.task_repo.delete_by_project(project_id, user_id)
        deleted = self.project_repo.delete(project_id, user_id)
        if not deleted:
            raise ValidationError("Projeto não encontrado.")


# ============================================================
# TASK SERVICE
# ============================================================

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
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")

        for task in project.list_tasks():
            if task.name == task_name:
                return task

        raise ValidationError("Tarefa não encontrada.")

    def add_task(
        self,
        *,
        project_id: int,
        user_id: str,
        name: str,
        planned_start: datetime,
        planned_end: datetime,
        cost: float = 0.0,
    ) -> Task:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")

        task = project.start_new_task(
            name=name,
            planned_start=planned_start,
            planned_end=planned_end,
            cost=cost,
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
        task = self.get_task(project_id, user_id, task_name)

        if task.id is None:
            raise ValidationError("Task sem ID persistido.")

        return self.task_repo.list_time_entries(task.id)


# ============================================================
# ROUTINE ACTIVITY SERVICE
# ============================================================

class RoutineActivityService:
    def __init__(self, routine_repo: IRoutineActivityRepository):
        self.routine_repo = routine_repo

    def start_activity(
        self,
        *,
        user_id: str,
        tipo_atividade: str,
        descricao: str = "",
    ) -> RoutineActivity:
        current = self.routine_repo.get_current(user_id)
        if current is not None:
            raise ValidationError("Ja existe uma atividade em andamento para este usuario.")

        activity = RoutineActivity(
            user_id=user_id,
            tipo_atividade=tipo_atividade,
            descricao=descricao,
        )
        self.routine_repo.save(activity)
        return activity

    def get_current_activity(self, user_id: str) -> Optional[RoutineActivity]:
        return self.routine_repo.get_current(user_id)

    def finish_current_activity(self, user_id: str) -> RoutineActivity:
        current = self.routine_repo.get_current(user_id)
        if current is None:
            raise ValidationError("Nao ha atividade em andamento para finalizar.")

        finished_at = datetime.now(timezone.utc)
        if finished_at < current.inicio:
            raise ValidationError("Fim da atividade nao pode ser anterior ao inicio.")

        hours = round((finished_at - current.inicio).total_seconds() / 3600, 10)

        finished = self.routine_repo.finish_current(
            user_id=user_id,
            finished_at=finished_at,
            hours=hours,
        )
        if finished is None:
            raise ValidationError("Nao ha atividade em andamento para finalizar.")
        return finished
