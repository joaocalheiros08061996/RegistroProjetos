from datetime import datetime
from pydantic import BaseModel

from domain.enums import (
    ProjectType,
    Severity,
    Urgency,
    Trend,
    ObjectiveClarity,
    MethodClarity,
)


# ============================================================
# INPUT DTOS
# ============================================================

class CreateProjectDTO(BaseModel):
    """
    DTO de entrada para criação de um projeto.
    """

    name: str
    project_type: ProjectType
    responsible_login: str
    fte: float

    planned_start: datetime
    planned_end: datetime

    # classificação GUT
    severity: Severity = Severity.NONE
    urgency: Urgency = Urgency.CAN_WAIT
    trend: Trend = Trend.STABLE

    # NOVOS CAMPOS
    objective_clarity: ObjectiveClarity = ObjectiveClarity.FULLY_DEFINED
    method_clarity: MethodClarity = MethodClarity.FULLY_DEFINED

    estimated_cost: float = 0.0


class CreateTaskDTO(BaseModel):
    """
    DTO de entrada para criação de uma tarefa.
    """

    name: str
    planned_start: datetime
    planned_end: datetime
    cost: float = 0.0


# ============================================================
# TASK OUTPUT
# ============================================================

class TaskResponseDTO(BaseModel):
    """
    DTO de resposta contendo os dados de uma tarefa.

    Observações importantes:
    - `status` é a fonte da verdade da tarefa.
    - `percent_completed` é DERIVADO DO STATUS:
        * 0.0  -> tarefa não concluída
        * 100.0 -> tarefa concluída
    - Tempo real NÃO influencia o percentual de conclusão.
    """

    name: str
    status: str

    planned_start: datetime
    planned_end: datetime
    cost: float

    # esforço
    actual_seconds: float
    time_entries_count: int

    # progresso semântico
    percent_completed: float


# ============================================================
# PROJECT OUTPUT (LIST / SUMMARY)
# ============================================================

class ProjectSummaryResponseDTO(BaseModel):
    """
    DTO resumido de projeto (ex: listas simples).
    """

    id: int
    name: str
    task_count: int


class ProjectListItemResponseDTO(BaseModel):
    """
    DTO de projeto para listagens.
    """

    id: int
    name: str
    project_type: str

    responsible_login: str

    planned_start: datetime
    planned_end: datetime

    estimated_cost: float

    task_count: int

    # progresso semântico
    percent_completed: float


# ============================================================
# PROJECT OUTPUT (METRICS / DETAIL)
# ============================================================

class ProjectMetricsResponseDTO(BaseModel):
    """
    DTO contendo métricas agregadas de um projeto.

    Observações:
    - `percent_completed` é baseado EXCLUSIVAMENTE
      no número de tarefas concluídas.
    - `actual_days` representa esforço real acumulado.
    """

    percent_completed: float
    actual_days: float
    task_count: int

    # nomes das tarefas ainda não concluídas
    active_tasks: list[str]


class ProjectDetailResponseDTO(BaseModel):
    """
    DTO detalhado de um projeto.
    """

    id: int
    name: str
    project_type: str

    responsible_login: str
    fte: float

    planned_start: datetime
    planned_end: datetime

    # classificação GUT
    severity: str
    urgency: str
    trend: str

    # NOVOS CAMPOS
    objective_clarity: str
    method_clarity: str

    estimated_cost: float

    # métricas
    task_count: int
    percent_completed: float
    actual_days: float

    # tarefas não concluídas
    active_tasks: list[str]

    # todas as tarefas
    tasks: list[TaskResponseDTO]
