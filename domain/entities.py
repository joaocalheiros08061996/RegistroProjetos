from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .enums import (
    MethodClarity,
    ObjectiveClarity,
    ProcessClassification,
    ProjectType,
    Severity,
    TaskStatus,
    Trend,
    Urgency,
)
from .exceptions import (
    TaskAlreadyCompletedError,
    TaskAlreadyStartedError,
    TaskNotStartedError,
    ValidationError,
)
from .responsible import normalize_responsible_name


# ============================================================
# TIME ENTRY
# ============================================================

class TimeEntry:
    def __init__(self, start: datetime):
        self.start: datetime = start
        self.end: Optional[datetime] = None

    def _normalize_like_start(self, value: datetime) -> datetime:
        """
        Normaliza `value` para o mesmo "tipo de timezone" de `self.start`.
        - Se `start` for aware, tratamos naive como UTC.
        - Se `start` for naive, convertendo aware para naive em UTC.
        """
        start_is_aware = self.start.tzinfo is not None and self.start.tzinfo.utcoffset(self.start) is not None
        value_is_aware = value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

        if start_is_aware:
            if not value_is_aware:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(self.start.tzinfo)

        if value_is_aware:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def stop(self, end: datetime) -> None:
        end = self._normalize_like_start(end)
        if self.end is not None:
            raise ValidationError("TimeEntry ja finalizado.")
        if end < self.start:
            raise ValidationError("End < start para TimeEntry.")
        self.end = end

    @property
    def duration(self) -> timedelta:
        if self.end is None:
            if self.start.tzinfo is not None and self.start.tzinfo.utcoffset(self.start) is not None:
                return datetime.now(tz=self.start.tzinfo) - self.start
            return datetime.utcnow() - self.start
        return self.end - self.start


# ============================================================
# TASK
# ============================================================

class Task:
    def __init__(
        self,
        name: str,
        planned_start: datetime,
        planned_end: datetime,
        cost: float = 0.0,
    ):
        if not name or not name.strip():
            raise ValidationError("Nome da tarefa obrigatorio.")
        if planned_end < planned_start:
            raise ValidationError("Data final planejada anterior a inicial.")

        self._id: Optional[int] = None
        self._name: str = name.strip()
        self._planned_start: datetime = planned_start
        self._planned_end: datetime = planned_end
        self.cost: float = float(cost)

        self._status: TaskStatus = TaskStatus.PLANNED
        self._time_entries: List[TimeEntry] = []
        self._current_entry: Optional[TimeEntry] = None

    # ---------- Identidade ----------

    @property
    def id(self) -> Optional[int]:
        return self._id

    def _set_id(self, id_value: int) -> None:
        if self._id is not None:
            raise ValidationError("Id ja definido.")
        self._id = int(id_value)

    # ---------- Hidratação (repositórios) ----------

    def _set_status(self, status: TaskStatus | str) -> None:
        self._status = TaskStatus(status)
        if self._status != TaskStatus.IN_PROGRESS:
            self._current_entry = None

    def _add_time_entry(self, entry: TimeEntry) -> None:
        self._time_entries.append(entry)
        if entry.end is None:
            self._current_entry = entry
            self._status = TaskStatus.IN_PROGRESS

    # ---------- Propriedades ----------

    @property
    def name(self) -> str:
        return self._name

    @property
    def planned_start(self) -> datetime:
        return self._planned_start

    @property
    def planned_end(self) -> datetime:
        return self._planned_end

    @property
    def status(self) -> TaskStatus:
        return self._status

    # ---------- Controle de tempo ----------

    def start(self, when: Optional[datetime] = None) -> None:
        if self._status == TaskStatus.COMPLETED:
            raise TaskAlreadyCompletedError("Tarefa ja concluida.")
        if self._current_entry is not None:
            raise TaskAlreadyStartedError("Tarefa ja iniciada.")

        now = when or datetime.utcnow()
        entry = TimeEntry(start=now)
        self._time_entries.append(entry)
        self._current_entry = entry
        self._status = TaskStatus.IN_PROGRESS

    def stop(self, when: Optional[datetime] = None) -> timedelta:
        if self._current_entry is None:
            raise TaskNotStartedError("Nenhuma entrada em andamento para parar.")

        now = when or datetime.utcnow()
        self._current_entry.stop(now)
        duration = self._current_entry.duration
        self._current_entry = None

        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.PAUSED

        return duration

    def add_manual_entry(self, start: datetime, end: datetime) -> None:
        if end < start:
            raise ValidationError("End < start em add_manual_entry.")
        entry = TimeEntry(start=start)
        entry.stop(end)
        self._time_entries.append(entry)

    # ---------- Métricas de tempo ----------

    @property
    def time_entries(self) -> List[TimeEntry]:
        return list(self._time_entries)

    @property
    def actual_time(self) -> timedelta:
        total = timedelta()
        for te in self._time_entries:
            total += te.duration
        return total

    @property
    def planned_duration(self) -> timedelta:
        return self._planned_end - self._planned_start

    # ---------- Progresso (SEMÂNTICO) ----------

    @property
    def is_completed(self) -> bool:
        return self._status == TaskStatus.COMPLETED

    @property
    def percent_completed(self) -> float:
        return 100.0 if self.is_completed else 0.0

    def mark_completed(self) -> None:
        if self._status == TaskStatus.COMPLETED:
            raise TaskAlreadyCompletedError("Tarefa ja esta concluida.")
        if self._current_entry is not None:
            self.stop()
        self._status = TaskStatus.COMPLETED


# ============================================================
# PROJECT
# ============================================================

class Project:
    _GUT_SEVERITY_WEIGHTS = {
        Severity.NONE.value: 1,
        Severity.NONE.name: 1,
        Severity.LOW.value: 2,
        Severity.LOW.name: 2,
        Severity.MEDIUM.value: 3,
        Severity.MEDIUM.name: 3,
        Severity.HIGH.value: 4,
        Severity.HIGH.name: 4,
        Severity.CRITICAL.value: 5,
        Severity.CRITICAL.name: 5,
    }
    _GUT_URGENCY_WEIGHTS = {
        Urgency.CAN_WAIT.value: 1,
        Urgency.CAN_WAIT.name: 1,
        Urgency.LOW.value: 2,
        Urgency.LOW.name: 2,
        Urgency.MEDIUM.value: 3,
        Urgency.MEDIUM.name: 3,
        Urgency.FAST.value: 4,
        Urgency.FAST.name: 4,
        Urgency.IMMEDIATE.value: 5,
        Urgency.IMMEDIATE.name: 5,
    }
    _GUT_TREND_WEIGHTS = {
        Trend.STABLE.value: 1,
        Trend.STABLE.name: 1,
        Trend.LONG_TERM.value: 2,
        Trend.LONG_TERM.name: 2,
        Trend.MEDIUM_TERM.value: 3,
        Trend.MEDIUM_TERM.name: 3,
        Trend.SHORT_TERM.value: 4,
        Trend.SHORT_TERM.name: 4,
        Trend.RAPID.value: 5,
        Trend.RAPID.name: 5,
    }
    _COMPLEXITY_OBJECTIVE_WEIGHTS = {
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
    _COMPLEXITY_METHOD_WEIGHTS = {
        MethodClarity.FULLY_DEFINED.value: 1,
        MethodClarity.FULLY_DEFINED.name: 1,
        MethodClarity.KNOWN_WITH_ADAPTATIONS.value: 2,
        MethodClarity.KNOWN_WITH_ADAPTATIONS.name: 2,
        MethodClarity.PARTIALLY_KNOWN.value: 3,
        MethodClarity.PARTIALLY_KNOWN.name: 3,
        MethodClarity.POORLY_DEFINED.value: 4,
        MethodClarity.POORLY_DEFINED.name: 4,
        MethodClarity.UNKNOWN.value: 5,
        MethodClarity.UNKNOWN.name: 5,
    }

    def __init__(
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
    ):
        if not user_id or not user_id.strip():
            raise ValidationError("User ID do projeto e obrigatorio.")

        if not name or not name.strip():
            raise ValidationError("Nome do projeto obrigatorio.")

        if planned_end < planned_start:
            raise ValidationError("Data final do projeto anterior a inicial.")

        try:
            numeric_fte = float(fte)
        except (TypeError, ValueError) as exc:
            raise ValidationError("FTE deve ser um numero inteiro.") from exc

        if numeric_fte <= 0:
            raise ValidationError("FTE deve ser maior que zero.")

        if not numeric_fte.is_integer():
            raise ValidationError("FTE deve ser um numero inteiro.")

        self._id: Optional[int] = None

        self.user_id: str = user_id.strip()
        self._name: str = name.strip()

        self.project_type: ProjectType = project_type
        self.responsible_login: str = normalize_responsible_name(responsible_login)
        self.fte: int = int(numeric_fte)

        self.planned_start: datetime = planned_start
        self.planned_end: datetime = planned_end

        # Classificação GUT
        self.severity: Severity = severity
        self.urgency: Urgency = urgency
        self.trend: Trend = trend

        # NOVOS CAMPOS
        self.objective_clarity: ObjectiveClarity = objective_clarity
        self.method_clarity: MethodClarity = method_clarity
        self.process_classification: ProcessClassification | None = process_classification

        self.estimated_cost: float = float(estimated_cost)

        self._tasks: List[Task] = []

        self.created_at: datetime = datetime.utcnow()

    # ---------- Identidade ----------

    @property
    def id(self) -> Optional[int]:
        return self._id

    def _set_id(self, id_value: int) -> None:
        if self._id is not None:
            raise ValidationError("Id do projeto ja definido.")
        self._id = int(id_value)

    # ---------- Propriedades ----------

    @property
    def name(self) -> str:
        return self._name

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    # ---------- Tarefas ----------

    def add_task(self, task: Task) -> None:
        for existing in self._tasks:
            if existing.name == task.name:
                raise ValidationError(
                    f"Tarefa com nome '{task.name}' ja existe no projeto."
                )
        self._tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        self._tasks = [t for t in self._tasks if t.name != task_name]

    def list_tasks(self) -> List[Task]:
        return list(self._tasks)

    def active_tasks(self) -> List[Task]:
        return [t for t in self._tasks if not t.is_completed]

    def completed_tasks(self) -> List[Task]:
        return [t for t in self._tasks if t.is_completed]

    # ---------- Planejamento vs execução ----------

    @property
    def planned_duration(self) -> timedelta:
        return self.planned_end - self.planned_start

    def actual_days(self) -> float:
        total = timedelta()
        for task in self._tasks:
            total += task.actual_time
        return total.total_seconds() / 86400.0

    @staticmethod
    def _gut_weight(raw_value, mapping: dict[str, int]) -> int:
        if hasattr(raw_value, "value"):
            raw_value = raw_value.value
        return mapping.get(str(raw_value).strip(), 1)

    @property
    def gut_score(self) -> int:
        severity_weight = self._gut_weight(
            self.severity,
            self._GUT_SEVERITY_WEIGHTS,
        )
        urgency_weight = self._gut_weight(
            self.urgency,
            self._GUT_URGENCY_WEIGHTS,
        )
        trend_weight = self._gut_weight(
            self.trend,
            self._GUT_TREND_WEIGHTS,
        )
        return severity_weight * urgency_weight * trend_weight

    @property
    def priority_level(self) -> int:
        score = self.gut_score
        if score >= 101:
            return 1
        if score >= 76:
            return 2
        if score >= 51:
            return 3
        if score >= 26:
            return 4
        return 5

    @property
    def priority_label(self) -> str:
        return f"Prioridade {self.priority_level}"

    @staticmethod
    def _complexity_weight(raw_value, mapping: dict[str, int]) -> int:
        if hasattr(raw_value, "value"):
            raw_value = raw_value.value
        return mapping.get(str(raw_value).strip(), 1)

    @property
    def complexity_score(self) -> int:
        objective_weight = self._complexity_weight(
            self.objective_clarity,
            self._COMPLEXITY_OBJECTIVE_WEIGHTS,
        )
        method_weight = self._complexity_weight(
            self.method_clarity,
            self._COMPLEXITY_METHOD_WEIGHTS,
        )
        raw_score = objective_weight * method_weight
        return max(1, min(5, (raw_score + 4) // 5))

    @property
    def complexity_label(self) -> str:
        return f"Complexidade {self.complexity_score}"

    # ---------- Progresso (SEMÂNTICO) ----------

    @property
    def percent_completed(self) -> float:
        total = len(self._tasks)
        if total == 0:
            return 0.0

        completed = sum(1 for t in self._tasks if t.is_completed)
        return round((completed / total) * 100.0, 2)

    # ---------- Fábrica ----------

    def start_new_task(
        self,
        name: str,
        planned_start: datetime,
        planned_end: datetime,
        cost: float = 0.0,
    ) -> Task:

        task = Task(
            name=name,
            planned_start=planned_start,
            planned_end=planned_end,
            cost=cost,
        )

        self.add_task(task)

        return task
