# services.py

from datetime import datetime, timezone
from typing import Dict, List, Optional

from domain.entities import Project, Task
from domain.enums import (
    MethodClarity,
    ObjectiveClarity,
    ProcessClassification,
    ProjectType,
    Severity,
    TaskStatus,
    Trend,
    Urgency,
)
from domain.exceptions import ValidationError
from domain.repositories import (
    IDashboardRepository,
    IProjectRepository,
    IRoutineActivityRepository,
    ITaskRepository,
)
from domain.routine_activity import RoutineActivity


# ============================================================
# PROJECT SERVICE
# ============================================================

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
        responsavel: str = "",
        descricao: str = "",
    ) -> RoutineActivity:
        current = self.routine_repo.get_current(user_id)
        if current is not None:
            raise ValidationError("Ja existe uma atividade em andamento para este usuario.")

        activity = RoutineActivity(
            user_id=user_id,
            tipo_atividade=tipo_atividade,
            responsavel=responsavel,
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


# ============================================================
# DASHBOARD SERVICE
# ============================================================

class DashboardService:
    _MONTH_LABELS = {
        1: "JAN",
        2: "FEV",
        3: "MAR",
        4: "ABR",
        5: "MAI",
        6: "JUN",
        7: "JUL",
        8: "AGO",
        9: "SET",
        10: "OUT",
        11: "NOV",
        12: "DEZ",
    }

    _PROJECT_TYPE_LABELS = {
        "LAYOUT": "LAYOUT",
        "EXPORTACAO": "EXPORTAÇÃO",
        "NORMATIZACAO": "NORMATIZAÇÃO",
        "PADRONIZACAO": "PADRONIZAÇÃO",
        "TRY_OUT": "TRY OUT",
        "MAPEAMENTO": "MAPEAMENTO",
        "MELHORIA": "MELHORIA DE PROC. EXISTENTES",
        "MELHORIA_PROC_NOVOS": "MELHORIA DE PROC. NOVOS",
        "PECAS": "PEÇAS",
    }

    def __init__(self, dashboard_repo: IDashboardRepository):
        self.dashboard_repo = dashboard_repo

    def list_avg_real_days_by_project_type(self) -> list[dict]:
        rows = self.dashboard_repo.list_avg_real_days_by_project_type()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            average_days = float(row.get("average_days") or 0.0)

            if not project_type or average_days <= 0:
                continue

            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "average_days": average_days,
                }
            )

        items.sort(key=lambda item: item["average_days"], reverse=True)
        return items

    def list_avg_planned_vs_real_days_by_project_type(self) -> list[dict]:
        rows = self.dashboard_repo.list_avg_planned_vs_real_days_by_project_type()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            planned_average_days = float(row.get("planned_average_days") or 0.0)
            real_average_days = float(row.get("real_average_days") or 0.0)

            if not project_type:
                continue

            if planned_average_days <= 0 and real_average_days <= 0:
                continue

            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "planned_average_days": planned_average_days,
                    "real_average_days": real_average_days,
                }
            )

        items.sort(
            key=lambda item: (
                item["real_average_days"],
                item["planned_average_days"],
            ),
            reverse=True,
        )
        return items

    def list_routine_total_days_by_month(self) -> list[dict]:
        rows = self.dashboard_repo.list_routine_total_days_by_month()

        items: list[dict] = []
        for row in rows:
            user_id = str(row.get("user_id") or "").strip()
            user_label = str(row.get("user_label") or "").strip()
            activity_type = str(row.get("activity_type") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            total_days = float(row.get("total_days") or 0.0)

            if not user_id or not activity_type or year <= 0 or month not in self._MONTH_LABELS:
                continue

            if total_days <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "user_id": user_id,
                    "user_label": user_label or self._format_user_label(user_id),
                    "activity_type": activity_type,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "total_days": total_days,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["activity_type"],
                item["user_id"],
            )
        )
        return items

    @staticmethod
    def _format_user_label(user_id: str) -> str:
        if len(user_id) > 12:
            return f"Usuário {user_id[:4]}...{user_id[-4:]}"
        return user_id or "Sem usuário"

    def list_project_monthly_kpis(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_monthly_kpis()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)

            if not project_type or not responsible_login:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "project_count": max(0, int(row.get("project_count") or 0)),
                    "planned_days_sum": max(0.0, float(row.get("planned_days_sum") or 0.0)),
                    "planned_days_count": max(0, int(row.get("planned_days_count") or 0)),
                    "real_days_sum": max(0.0, float(row.get("real_days_sum") or 0.0)),
                    "real_days_count": max(0, int(row.get("real_days_count") or 0)),
                    "sla_breach_count": max(0, int(row.get("sla_breach_count") or 0)),
                    "sla_project_count": max(0, int(row.get("sla_project_count") or 0)),
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
            )
        )
        return items

    def list_project_complexity_counts(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_complexity_counts()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            complexity_score = int(row.get("complexity_score") or 0)
            project_count = int(row.get("project_count") or 0)

            if not project_type or complexity_score < 1 or complexity_score > 5:
                continue

            if project_count <= 0:
                continue

            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "complexity_score": complexity_score,
                    "project_count": project_count,
                }
            )

        items.sort(
            key=lambda item: (
                item["project_type_label"],
                item["complexity_score"],
            )
        )
        return items

    def list_project_complexity_counts_by_month(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_complexity_counts_by_month()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            complexity_score = int(row.get("complexity_score") or 0)
            project_count = int(row.get("project_count") or 0)

            if not project_type or not responsible_login:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            if complexity_score < 1 or complexity_score > 5:
                continue

            if project_count <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "complexity_score": complexity_score,
                    "project_count": project_count,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
                item["complexity_score"],
            )
        )
        return items

    def list_projects_by_responsible(self) -> list[dict]:
        rows = self.dashboard_repo.list_projects_by_responsible()

        items: list[dict] = []
        for row in rows:
            project_id = int(row.get("project_id") or 0)
            project_name = str(row.get("project_name") or "").strip()
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            planned_start = row.get("planned_start")
            planned_end = row.get("planned_end")
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)

            if project_id <= 0 or not project_name or not project_type:
                continue

            if not responsible_login:
                responsible_login = "Sem responsável"

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            task_count = max(0, int(row.get("task_count") or 0))
            completed_task_count = max(0, int(row.get("completed_task_count") or 0))
            percent_completed = max(0.0, min(100.0, float(row.get("percent_completed") or 0.0)))
            gut_score = max(1, int(row.get("gut_score") or 1))
            priority_level = int(row.get("priority_level") or 5)
            if priority_level < 1 or priority_level > 5:
                priority_level = 5
            complexity_score = int(row.get("complexity_score") or 1)
            if complexity_score < 1 or complexity_score > 5:
                complexity_score = 1

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "planned_start": planned_start,
                    "planned_end": planned_end,
                    "estimated_cost": max(0.0, float(row.get("estimated_cost") or 0.0)),
                    "task_count": task_count,
                    "completed_task_count": min(completed_task_count, task_count),
                    "percent_completed": round(percent_completed, 2),
                    "gut_score": gut_score,
                    "priority_level": priority_level,
                    "priority_label": str(
                        row.get("priority_label")
                        or f"Prioridade {priority_level}"
                    ),
                    "complexity_score": complexity_score,
                    "complexity_label": str(
                        row.get("complexity_label")
                        or f"Complexidade {complexity_score}"
                    ),
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                }
            )

        items.sort(
            key=lambda item: (
                item["responsible_login"],
                item["year"],
                item["month"],
                item["priority_level"],
                item["project_name"],
            )
        )
        return items

    def list_project_earned_value(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_earned_value()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            project_name = str(row.get("project_name") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)

            if not project_type or not responsible_login or not project_name:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            estimated_cost = max(0.0, float(row.get("estimated_cost") or 0.0))
            planned_value = max(0.0, float(row.get("planned_value") or 0.0))
            earned_value = max(0.0, float(row.get("earned_value") or 0.0))
            total_task_cost = max(0.0, float(row.get("total_task_cost") or 0.0))

            if estimated_cost <= 0 and total_task_cost <= 0 and planned_value <= 0 and earned_value <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_id": int(row.get("project_id") or 0),
                    "project_name": project_name,
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "estimated_cost": estimated_cost,
                    "planned_value": planned_value,
                    "earned_value": earned_value,
                    "total_task_cost": total_task_cost,
                    "task_count": max(0, int(row.get("task_count") or 0)),
                    "completed_task_count": max(0, int(row.get("completed_task_count") or 0)),
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
                item["project_name"],
            )
        )
        return items

    def list_project_effort_deviation(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_effort_deviation()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            task_count = max(0, int(row.get("task_count") or 0))
            planned_effort_hours = max(0.0, float(row.get("planned_effort_hours") or 0.0))
            actual_effort_hours = max(0.0, float(row.get("actual_effort_hours") or 0.0))

            if not project_type or not responsible_login:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            if task_count <= 0 or planned_effort_hours <= 0 or actual_effort_hours <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "task_count": task_count,
                    "planned_effort_hours": planned_effort_hours,
                    "actual_effort_hours": actual_effort_hours,
                    "effort_deviation_hours": actual_effort_hours - planned_effort_hours,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
            )
        )
        return items
