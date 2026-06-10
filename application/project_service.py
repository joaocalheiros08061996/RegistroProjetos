from datetime import datetime
import time
from typing import Dict, List

from application.performance import log_perf
from domain.project import Project
from domain.enums import (
    MethodClarity,
    ObjectiveClarity,
    ProcessClassification,
    ProjectType,
    Severity,
    Trend,
    Urgency,
)
from domain.exceptions import ValidationError
from domain.repositories import IProjectRepository, ITaskRepository


class ProjectService:
    LEGACY_PROJECT_TYPES = {
        ProjectType.MELHORIA,
        ProjectType.MELHORIA_PROC_NOVOS,
    }

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
        process_classification: ProcessClassification | None = None,
        estimated_cost: float = 0.0,
        description: str = "",
    ) -> Project:
        if project_type in self.LEGACY_PROJECT_TYPES:
            raise ValidationError(
                "Tipo de projeto legado nao permitido para novos cadastros."
            )

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
            process_classification=process_classification,
            estimated_cost=estimated_cost,
            description=description,
        )

        self.project_repo.save(project)
        return project

    def list_projects_for_user(self, user_id: str) -> List[Project]:
        return self.project_repo.list_by_user(user_id)

    def list_project_summaries_for_user(self, user_id: str) -> list[dict]:
        started_at = time.perf_counter()
        projects = self.project_repo.list_summary_by_user(user_id)
        log_perf(
            "projects.list_summary",
            started_at,
            user_id=user_id,
            project_count=len(projects),
        )
        return projects

    def get_project(self, project_id: int, user_id: str) -> Project:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")
        return project

    def get_project_metrics(self, project_id: int, user_id: str) -> Dict:
        started_at = time.perf_counter()
        summary = self.project_repo.find_detail_summary(project_id, user_id)
        if not summary:
            raise ValidationError("Projeto não encontrado.")

        log_perf(
            "projects.metrics_summary",
            started_at,
            project_id=project_id,
            task_count=summary["task_count"],
        )
        return {
            "percent_completed": summary["percent_completed"],
            "actual_days": summary["actual_days"],
            "task_count": summary["task_count"],
            "active_tasks": summary["active_tasks"],
        }

    def get_project_detail(self, project_id: int, user_id: str) -> dict:
        started_at = time.perf_counter()
        detail = self.project_repo.find_detail_summary(project_id, user_id)
        if not detail:
            raise ValidationError("Projeto não encontrado.")

        task_count = int(detail.get("task_count") or 0)
        include_completed = task_count <= 10
        tasks = self.task_repo.list_with_time_summary(
            project_id,
            user_id,
            include_completed=include_completed,
        )
        detail = dict(detail)
        detail["tasks"] = tasks

        log_perf(
            "projects.detail_summary",
            started_at,
            project_id=project_id,
            task_count=task_count,
            returned_task_count=len(tasks),
            include_completed=include_completed,
        )
        return detail

    def delete_project(self, project_id: int, user_id: str) -> None:
        project = self.project_repo.find_by_id(project_id, user_id)
        if not project:
            raise ValidationError("Projeto não encontrado.")

        self.task_repo.delete_by_project(project_id, user_id)
        deleted = self.project_repo.delete(project_id, user_id)
        if not deleted:
            raise ValidationError("Projeto não encontrado.")
