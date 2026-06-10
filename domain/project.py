"""Entidade de projeto e regras agregadas de tarefas, prioridade e complexidade."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from .enums import (
    MethodClarity,
    ObjectiveClarity,
    ProcessClassification,
    ProjectType,
    Severity,
    Trend,
    Urgency,
)
from .exceptions import ValidationError
from .responsible import normalize_responsible_name
from .task import Task
from .validation import PROJECT_DESCRIPTION_MAX_LENGTH


class Project:
    """Agrupa dados de planejamento, classificação e tarefas de um projeto."""

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
        description: str = "",
    ):
        """Cria um projeto validando identidade, FTE, datas e campos textuais."""
        if not user_id or not user_id.strip():
            raise ValidationError("User ID do projeto e obrigatorio.")

        if not name or not name.strip():
            raise ValidationError("Nome do projeto obrigatorio.")
        normalized_description = str(description or "").strip()
        if len(normalized_description) > PROJECT_DESCRIPTION_MAX_LENGTH:
            raise ValidationError("Descricao do projeto excede o tamanho permitido.")

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
        self._description: str = normalized_description

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
        """Retorna o identificador persistido do projeto, quando existir."""
        return self._id

    def _set_id(self, id_value: int) -> None:
        """Define o ID durante hidratação/persistência sem permitir sobrescrita."""
        if self._id is not None:
            raise ValidationError("Id do projeto ja definido.")
        self._id = int(id_value)

    # ---------- Propriedades ----------

    @property
    def name(self) -> str:
        """Retorna o nome normalizado do projeto."""
        return self._name

    @property
    def description(self) -> str:
        """Retorna a descrição normalizada do projeto."""
        return self._description

    @property
    def task_count(self) -> int:
        """Retorna a quantidade de tarefas associadas ao projeto."""
        return len(self._tasks)

    # ---------- Tarefas ----------

    def add_task(self, task: Task) -> None:
        """Adiciona uma tarefa impedindo nomes duplicados dentro do projeto."""
        for existing in self._tasks:
            if existing.name == task.name:
                raise ValidationError(
                    f"Tarefa com nome '{task.name}' ja existe no projeto."
                )
        self._tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        """Remove tarefas com o nome informado da coleção em memória."""
        self._tasks = [t for t in self._tasks if t.name != task_name]

    def list_tasks(self) -> List[Task]:
        """Retorna uma cópia das tarefas do projeto."""
        return list(self._tasks)

    def active_tasks(self) -> List[Task]:
        """Retorna tarefas que ainda não foram concluídas."""
        return [t for t in self._tasks if not t.is_completed]

    def completed_tasks(self) -> List[Task]:
        """Retorna tarefas já concluídas."""
        return [t for t in self._tasks if t.is_completed]

    # ---------- Planejamento vs execução ----------

    @property
    def planned_duration(self) -> timedelta:
        """Calcula a duração planejada do projeto."""
        return self.planned_end - self.planned_start

    def actual_days(self) -> float:
        """Soma o tempo real das tarefas e converte para dias corridos."""
        total = timedelta()
        for task in self._tasks:
            total += task.actual_time
        return total.total_seconds() / 86400.0

    @staticmethod
    def _gut_weight(raw_value, mapping: dict[str, int]) -> int:
        """Obtém o peso GUT de valores enum ou texto legado."""
        if hasattr(raw_value, "value"):
            raw_value = raw_value.value
        return mapping.get(str(raw_value).strip(), 1)

    @property
    def gut_score(self) -> int:
        """Calcula a pontuação GUT a partir de gravidade, urgência e tendência."""
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
        """Converte a pontuação GUT no nível de prioridade de 1 a 5."""
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
        """Retorna o rótulo exibido para a prioridade calculada."""
        return f"Prioridade {self.priority_level}"

    @staticmethod
    def _complexity_weight(raw_value, mapping: dict[str, int]) -> int:
        """Obtém o peso de complexidade de valores enum ou texto legado."""
        if hasattr(raw_value, "value"):
            raw_value = raw_value.value
        return mapping.get(str(raw_value).strip(), 1)

    @property
    def complexity_score(self) -> int:
        """Calcula a complexidade combinando clareza de objetivo e método."""
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
        """Retorna o rótulo exibido para a complexidade calculada."""
        return f"Complexidade {self.complexity_score}"

    # ---------- Progresso (SEMÂNTICO) ----------

    @property
    def percent_completed(self) -> float:
        """Calcula progresso semântico pela proporção de tarefas concluídas."""
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
        description: str = "",
    ) -> Task:
        """Cria e associa uma nova tarefa ao projeto."""

        task = Task(
            name=name,
            planned_start=planned_start,
            planned_end=planned_end,
            cost=cost,
            description=description,
        )

        self.add_task(task)

        return task
