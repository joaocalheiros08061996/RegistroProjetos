from datetime import datetime, timezone
from typing import Dict, List, Optional

from domain.entities import Project, Task, TimeEntry
from domain.exceptions import ValidationError
from domain.enums import MethodClarity, ObjectiveClarity, TaskStatus
from domain.repositories import (
    IDashboardRepository,
    IProjectRepository,
    IRoutineActivityRepository,
    ITaskRepository,
)
from domain.routine_activity import RoutineActivity


class InMemoryProjectRepository(IProjectRepository):
    def __init__(self):
        self._storage: Dict[int, Project] = {}
        self._next_id = 1

    def save(self, project: Project) -> int:
        if project.id is None:
            project._set_id(self._next_id)
            self._next_id += 1
        self._storage[project.id] = project
        return project.id

    def find_by_id(self, project_id: int, user_id: str) -> Optional[Project]:
        project = self._storage.get(project_id)
        if project and project.user_id == user_id:
            return project
        return None

    def list_by_user(self, user_id: str) -> List[Project]:
        return [
            project
            for project in self._storage.values()
            if project.user_id == user_id
        ]

    def delete(self, project_id: int, user_id: str) -> bool:
        project = self._storage.get(project_id)
        if not project or project.user_id != user_id:
            return False
        del self._storage[project_id]
        return True


class InMemoryTaskRepository(ITaskRepository):
    def __init__(self):
        self._storage: Dict[int, Dict[int, Task]] = {}
        self._project_owners: Dict[int, str] = {}
        self._next_id = 1

    def save(self, task: Task, project_id: int, user_id: str) -> int:
        if project_id not in self._storage:
            self._storage[project_id] = {}
            self._project_owners[project_id] = user_id

        if task.id is None:
            task._set_id(self._next_id)
            self._next_id += 1

        self._storage[project_id][task.id] = task
        return task.id

    def find_by_id(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
    ) -> Optional[Task]:
        owner = self._project_owners.get(project_id)
        if owner is not None and owner != user_id:
            return None
        return self._storage.get(project_id, {}).get(task_id)

    def delete_by_name(self, project_id: int, user_id: str, task_name: str) -> bool:
        owner = self._project_owners.get(project_id)
        if owner is not None and owner != user_id:
            return False

        tasks = self._storage.get(project_id, {})
        task_id_to_remove = next(
            (task_id for task_id, task in tasks.items() if task.name == task_name),
            None,
        )
        if task_id_to_remove is None:
            return False

        del tasks[task_id_to_remove]
        if not tasks:
            self._storage.pop(project_id, None)
            self._project_owners.pop(project_id, None)
        return True

    def delete_by_project(self, project_id: int, user_id: str) -> int:
        owner = self._project_owners.get(project_id)
        if owner is not None and owner != user_id:
            return 0

        tasks = self._storage.pop(project_id, {})
        self._project_owners.pop(project_id, None)
        return len(tasks)

    def append_time_entry(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
        entry: TimeEntry,
    ) -> None:
        task = self.find_by_id(task_id, project_id, user_id)
        if not task:
            raise ValueError("Task not found")
        task._add_time_entry(entry)

    def update_status(self, task_id: int, status: str) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        task._set_status(TaskStatus(status))

    def start_time_entry(self, task_id: int, start: datetime) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        # In-memory repo persiste apenas; regra de dominio ja foi aplicada no service.
        # Mantemos no-op para evitar aplicar transicao de estado duas vezes.
        return None

    def close_open_time_entry(self, task_id: int, end: datetime) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        # Sem entrada aberta, o comportamento persistente esperado e no-op.
        return None

    def list_time_entries(self, task_id: int) -> list[tuple]:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        return [(e.start, e.end) for e in task.time_entries]

    def _find_task(self, task_id: int) -> Optional[Task]:
        for tasks in self._storage.values():
            if task_id in tasks:
                return tasks[task_id]
        return None


class InMemoryRoutineActivityRepository(IRoutineActivityRepository):
    def __init__(self):
        self._storage: Dict[int, RoutineActivity] = {}
        self._next_id = 1

    def save(self, activity: RoutineActivity) -> int:
        current = self.get_current(activity.user_id)
        if current is not None:
            raise ValidationError("Ja existe uma atividade em andamento para este usuario.")

        if activity.id is None:
            activity._set_id(self._next_id)
            self._next_id += 1

        self._storage[activity.id] = activity
        return activity.id

    def get_current(self, user_id: str) -> Optional[RoutineActivity]:
        active_items = [
            item
            for item in self._storage.values()
            if item.user_id == user_id and item.fim is None
        ]
        if not active_items:
            return None

        active_items.sort(key=lambda item: item.id or 0, reverse=True)
        return active_items[0]

    def finish_current(
        self,
        user_id: str,
        finished_at: datetime,
        hours: float,
    ) -> Optional[RoutineActivity]:
        current = self.get_current(user_id)
        if current is None:
            return None

        current.fim = finished_at
        current.horas_trabalhadas = hours
        return current


class InMemoryDashboardRepository(IDashboardRepository):
    def __init__(
        self,
        project_repo: InMemoryProjectRepository,
        routine_repo: Optional[InMemoryRoutineActivityRepository] = None,
    ):
        self.project_repo = project_repo
        self.routine_repo = routine_repo

    def list_avg_real_days_by_project_type(self) -> list[dict]:
        grouped_by_type: dict[str, list[float]] = {}

        for project in self.project_repo._storage.values():
            total_seconds = 0.0

            for task in project.list_tasks():
                for entry in task.time_entries:
                    if entry.end is None:
                        continue
                    total_seconds += max(
                        0.0,
                        (entry.end - entry.start).total_seconds(),
                    )

            if total_seconds <= 0:
                continue

            project_type = project.project_type.value
            grouped_by_type.setdefault(project_type, []).append(
                total_seconds / 86400.0
            )

        rows: list[dict] = []
        for project_type, real_days_values in grouped_by_type.items():
            if not real_days_values:
                continue
            average_days = sum(real_days_values) / len(real_days_values)
            rows.append(
                {
                    "project_type": project_type,
                    "average_days": float(average_days),
                }
            )

        rows.sort(key=lambda item: item["average_days"], reverse=True)
        return rows

    def list_avg_planned_vs_real_days_by_project_type(self) -> list[dict]:
        grouped_planned_by_type: Dict[str, list[float]] = {}
        grouped_real_by_type: Dict[str, list[float]] = {}

        for project in self.project_repo._storage.values():
            project_type = project.project_type.value

            planned_days = (project.planned_end - project.planned_start).total_seconds() / 86400.0
            if planned_days > 0:
                grouped_planned_by_type.setdefault(project_type, []).append(planned_days)

            total_seconds = 0.0
            for task in project.list_tasks():
                for entry in task.time_entries:
                    if entry.end is None:
                        continue
                    total_seconds += max(
                        0.0,
                        (entry.end - entry.start).total_seconds(),
                    )

            if total_seconds > 0:
                grouped_real_by_type.setdefault(project_type, []).append(total_seconds / 86400.0)

        all_types = set(grouped_planned_by_type.keys()) | set(grouped_real_by_type.keys())
        rows: list[dict] = []
        for project_type in all_types:
            planned_values = grouped_planned_by_type.get(project_type, [])
            real_values = grouped_real_by_type.get(project_type, [])

            planned_average = sum(planned_values) / len(planned_values) if planned_values else 0.0
            real_average = sum(real_values) / len(real_values) if real_values else 0.0

            if planned_average <= 0 and real_average <= 0:
                continue

            rows.append(
                {
                    "project_type": project_type,
                    "planned_average_days": float(planned_average),
                    "real_average_days": float(real_average),
                }
            )

        rows.sort(
            key=lambda item: (
                item["real_average_days"],
                item["planned_average_days"],
            ),
            reverse=True,
        )
        return rows

    def list_routine_total_days_by_month(self) -> list[dict]:
        if self.routine_repo is None:
            return []

        grouped: dict[tuple[str, str, str, int, int], float] = {}
        for activity in self.routine_repo._storage.values():
            hours = activity.horas_trabalhadas
            if (hours is None or hours <= 0) and activity.fim is not None:
                hours = max(
                    0.0,
                    (activity.fim - activity.inicio).total_seconds() / 3600.0,
                )

            if hours is None or hours <= 0:
                continue

            key = (
                activity.user_id,
                self._routine_user_label(activity),
                activity.tipo_atividade,
                activity.ano,
                activity.mes,
            )
            grouped[key] = grouped.get(key, 0.0) + (float(hours) / 24.0)

        rows = [
            {
                "user_id": user_id,
                "user_label": user_label,
                "activity_type": activity_type,
                "year": year,
                "month": month,
                "total_days": total_days,
            }
            for (user_id, user_label, activity_type, year, month), total_days in grouped.items()
        ]
        rows.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["activity_type"],
                item["user_label"],
                item["user_id"],
            )
        )
        return rows

    @staticmethod
    def _routine_user_label(activity: RoutineActivity) -> str:
        email = str(getattr(activity, "user_email", "") or "").strip()
        if email:
            return email

        user_id = str(activity.user_id or "").strip()
        if len(user_id) > 12:
            return f"Usuário {user_id[:4]}...{user_id[-4:]}"
        return user_id or "Sem usuário"

    def list_project_monthly_kpis(self) -> list[dict]:
        grouped: dict[tuple[str, str, int, int], dict] = {}

        for project in self.project_repo._storage.values():
            project_type = project.project_type.value
            responsible_login = project.responsible_login
            year = project.planned_start.year
            month = project.planned_start.month
            planned_days = (project.planned_end - project.planned_start).total_seconds() / 86400.0

            total_seconds = 0.0
            for task in project.list_tasks():
                for entry in task.time_entries:
                    if entry.end is None:
                        continue
                    total_seconds += max(
                        0.0,
                        (entry.end - entry.start).total_seconds(),
                    )
            real_days = total_seconds / 86400.0

            key = (project_type, responsible_login, year, month)
            row = grouped.setdefault(
                key,
                {
                    "project_type": project_type,
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "project_count": 0,
                    "planned_days_sum": 0.0,
                    "planned_days_count": 0,
                    "real_days_sum": 0.0,
                    "real_days_count": 0,
                    "sla_breach_count": 0,
                    "sla_project_count": 0,
                },
            )

            row["project_count"] += 1
            if real_days > 0:
                row["real_days_sum"] += real_days
                row["real_days_count"] += 1

                if planned_days > 0:
                    row["planned_days_sum"] += planned_days
                    row["planned_days_count"] += 1
                    row["sla_project_count"] += 1
                    if real_days > planned_days:
                        row["sla_breach_count"] += 1

        rows = list(grouped.values())
        rows.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type"],
                item["responsible_login"],
            )
        )
        return rows

    @staticmethod
    def _complexity_value(raw_value, mapping: dict[str, int]) -> int | None:
        if raw_value is None:
            return None

        if hasattr(raw_value, "value"):
            raw_value = raw_value.value

        value = str(raw_value).strip()
        return mapping.get(value)

    @staticmethod
    def _complexity_bucket(objective_score: int, method_score: int) -> int:
        raw_score = objective_score * method_score
        return max(1, min(5, (raw_score + 4) // 5))

    def list_project_complexity_counts(self) -> list[dict]:
        objective_values = {
            ObjectiveClarity.FULLY_DEFINED.value: 1,
            ObjectiveClarity.FULLY_DEFINED.name: 1,
            ObjectiveClarity.CLEAR_WITH_AMBIGUITIES.value: 2,
            ObjectiveClarity.CLEAR_WITH_AMBIGUITIES.name: 2,
            ObjectiveClarity.PARTIALLY_DEFINED.value: 3,
            ObjectiveClarity.PARTIALLY_DEFINED.name: 3,
            ObjectiveClarity.UNCLEAR.value: 4,
            ObjectiveClarity.UNCLEAR.name: 4,
            ObjectiveClarity.UNDEFINED.value: 5,
            ObjectiveClarity.UNDEFINED.name: 5,
        }
        method_values = {
            MethodClarity.FULLY_DEFINED.value: 1,
            MethodClarity.FULLY_DEFINED.name: 1,
            MethodClarity.KNOWN_WITH_ADAPTATIONS.value: 2,
            MethodClarity.KNOWN_WITH_ADAPTATIONS.name: 2,
            "Métodos definidos com pequenas alterações": 2,
            MethodClarity.PARTIALLY_KNOWN.value: 3,
            MethodClarity.PARTIALLY_KNOWN.name: 3,
            MethodClarity.POORLY_DEFINED.value: 4,
            MethodClarity.POORLY_DEFINED.name: 4,
            MethodClarity.UNKNOWN.value: 5,
            MethodClarity.UNKNOWN.name: 5,
        }

        grouped: dict[tuple[str, int], int] = {}
        for project in self.project_repo._storage.values():
            objective_score = self._complexity_value(
                project.objective_clarity,
                objective_values,
            )
            method_score = self._complexity_value(
                project.method_clarity,
                method_values,
            )

            if objective_score is None or method_score is None:
                continue

            project_type = project.project_type.value
            complexity_score = self._complexity_bucket(
                objective_score,
                method_score,
            )
            key = (project_type, complexity_score)
            grouped[key] = grouped.get(key, 0) + 1

        rows = [
            {
                "project_type": project_type,
                "complexity_score": complexity_score,
                "project_count": project_count,
            }
            for (project_type, complexity_score), project_count in grouped.items()
        ]
        rows.sort(
            key=lambda item: (
                item["project_type"],
                item["complexity_score"],
            )
        )
        return rows

    def list_project_complexity_counts_by_month(self) -> list[dict]:
        objective_values = {
            ObjectiveClarity.FULLY_DEFINED.value: 1,
            ObjectiveClarity.FULLY_DEFINED.name: 1,
            ObjectiveClarity.CLEAR_WITH_AMBIGUITIES.value: 2,
            ObjectiveClarity.CLEAR_WITH_AMBIGUITIES.name: 2,
            ObjectiveClarity.PARTIALLY_DEFINED.value: 3,
            ObjectiveClarity.PARTIALLY_DEFINED.name: 3,
            ObjectiveClarity.UNCLEAR.value: 4,
            ObjectiveClarity.UNCLEAR.name: 4,
            ObjectiveClarity.UNDEFINED.value: 5,
            ObjectiveClarity.UNDEFINED.name: 5,
        }
        method_values = {
            MethodClarity.FULLY_DEFINED.value: 1,
            MethodClarity.FULLY_DEFINED.name: 1,
            MethodClarity.KNOWN_WITH_ADAPTATIONS.value: 2,
            MethodClarity.KNOWN_WITH_ADAPTATIONS.name: 2,
            "Métodos definidos com pequenas alterações": 2,
            MethodClarity.PARTIALLY_KNOWN.value: 3,
            MethodClarity.PARTIALLY_KNOWN.name: 3,
            MethodClarity.POORLY_DEFINED.value: 4,
            MethodClarity.POORLY_DEFINED.name: 4,
            MethodClarity.UNKNOWN.value: 5,
            MethodClarity.UNKNOWN.name: 5,
        }

        grouped: dict[tuple[str, str, int, int, int], int] = {}
        for project in self.project_repo._storage.values():
            if project.planned_start is None:
                continue

            objective_score = self._complexity_value(
                project.objective_clarity,
                objective_values,
            )
            method_score = self._complexity_value(
                project.method_clarity,
                method_values,
            )

            if objective_score is None or method_score is None:
                continue

            complexity_score = self._complexity_bucket(
                objective_score,
                method_score,
            )
            project_type = project.project_type.value
            responsible_login = (project.responsible_login or "").strip() or "Sem responsável"
            key = (
                project_type,
                responsible_login,
                project.planned_start.year,
                project.planned_start.month,
                complexity_score,
            )
            grouped[key] = grouped.get(key, 0) + 1

        rows = [
            {
                "project_type": project_type,
                "responsible_login": responsible_login,
                "year": year,
                "month": month,
                "complexity_score": complexity_score,
                "project_count": project_count,
            }
            for (
                project_type,
                responsible_login,
                year,
                month,
                complexity_score,
            ), project_count in grouped.items()
        ]
        rows.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type"],
                item["responsible_login"],
                item["complexity_score"],
            )
        )
        return rows

    @staticmethod
    def _project_reference_now(project: Project) -> datetime:
        now = datetime.now(timezone.utc)
        start = project.planned_start
        if start.tzinfo is not None and start.tzinfo.utcoffset(start) is not None:
            return now.astimezone(start.tzinfo)
        return now.replace(tzinfo=None)

    @classmethod
    def _planned_progress(cls, project: Project) -> float:
        if project.planned_end <= project.planned_start:
            return 0.0

        now = cls._project_reference_now(project)
        if now <= project.planned_start:
            return 0.0
        if now >= project.planned_end:
            return 1.0

        total_seconds = (project.planned_end - project.planned_start).total_seconds()
        if total_seconds <= 0:
            return 0.0

        return max(0.0, min(1.0, (now - project.planned_start).total_seconds() / total_seconds))

    def list_project_earned_value(self) -> list[dict]:
        rows: list[dict] = []

        for project in self.project_repo._storage.values():
            tasks = project.list_tasks()
            total_task_cost = sum(max(0.0, float(task.cost or 0.0)) for task in tasks)
            completed_tasks = [task for task in tasks if task.is_completed]
            earned_value = sum(max(0.0, float(task.cost or 0.0)) for task in completed_tasks)
            estimated_cost = max(0.0, float(project.estimated_cost or 0.0))
            baseline_value = estimated_cost if estimated_cost > 0 else total_task_cost

            if baseline_value <= 0:
                continue

            rows.append(
                {
                    "project_id": project.id or 0,
                    "project_name": project.name,
                    "project_type": project.project_type.value,
                    "responsible_login": (project.responsible_login or "").strip() or "Sem responsável",
                    "year": project.planned_start.year,
                    "month": project.planned_start.month,
                    "estimated_cost": estimated_cost,
                    "planned_value": baseline_value * self._planned_progress(project),
                    "earned_value": earned_value,
                    "total_task_cost": total_task_cost,
                    "task_count": len(tasks),
                    "completed_task_count": len(completed_tasks),
                }
            )

        rows.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type"],
                item["responsible_login"],
                item["project_name"],
            )
        )
        return rows

    def list_project_effort_deviation(self) -> list[dict]:
        grouped: dict[tuple[str, str, int, int], dict] = {}

        for project in self.project_repo._storage.values():
            project_type = project.project_type.value
            responsible_login = (project.responsible_login or "").strip() or "Sem responsável"

            for task in project.list_tasks():
                planned_seconds = (task.planned_end - task.planned_start).total_seconds()
                if planned_seconds <= 0:
                    continue

                actual_seconds = 0.0
                for entry in task.time_entries:
                    if entry.end is None or entry.end <= entry.start:
                        continue
                    actual_seconds += (entry.end - entry.start).total_seconds()

                if actual_seconds <= 0:
                    continue

                key = (
                    project_type,
                    responsible_login,
                    task.planned_start.year,
                    task.planned_start.month,
                )
                row = grouped.setdefault(
                    key,
                    {
                        "project_type": project_type,
                        "responsible_login": responsible_login,
                        "year": task.planned_start.year,
                        "month": task.planned_start.month,
                        "task_count": 0,
                        "planned_effort_hours": 0.0,
                        "actual_effort_hours": 0.0,
                    },
                )
                row["task_count"] += 1
                row["planned_effort_hours"] += planned_seconds / 3600.0
                row["actual_effort_hours"] += actual_seconds / 3600.0

        rows = list(grouped.values())
        rows.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type"],
                item["responsible_login"],
            )
        )
        return rows
