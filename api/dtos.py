from datetime import datetime
from typing import Optional
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

    # matriz GUT / priorizacao
    gut_score: int
    priority_level: int
    priority_label: str


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


# ============================================================
# ROUTINE ACTIVITIES
# ============================================================

class StartRoutineActivityDTO(BaseModel):
    tipo_atividade: str
    responsavel: str = ""
    descricao: str = ""


class RoutineActivityResponseDTO(BaseModel):
    id: int
    tipo_atividade: str
    responsavel: str
    descricao: str
    inicio: datetime
    fim: Optional[datetime]
    ano: int
    mes: int
    dia: int
    horas_trabalhadas: Optional[float]


# ============================================================
# DASHBOARD
# ============================================================

class DashboardAvgRealDaysByTypeItemDTO(BaseModel):
    project_type: str
    project_type_label: str
    average_days: float


class DashboardAvgRealDaysByTypeResponseDTO(BaseModel):
    chart: str
    items: list[DashboardAvgRealDaysByTypeItemDTO]


class DashboardAvgPlannedVsRealDaysByTypeItemDTO(BaseModel):
    project_type: str
    project_type_label: str
    planned_average_days: float
    real_average_days: float


class DashboardAvgPlannedVsRealDaysByTypeResponseDTO(BaseModel):
    chart: str
    items: list[DashboardAvgPlannedVsRealDaysByTypeItemDTO]


class DashboardRoutineTotalDaysByMonthItemDTO(BaseModel):
    user_id: str
    user_label: str
    activity_type: str
    year: int
    month: int
    month_label: str
    period_label: str
    total_days: float


class DashboardRoutineTotalDaysByMonthResponseDTO(BaseModel):
    chart: str
    items: list[DashboardRoutineTotalDaysByMonthItemDTO]


class DashboardProjectMonthlyKpiItemDTO(BaseModel):
    project_type: str
    project_type_label: str
    responsible_login: str
    year: int
    month: int
    month_label: str
    period_label: str
    project_count: int
    planned_days_sum: float
    planned_days_count: int
    real_days_sum: float
    real_days_count: int
    sla_breach_count: int
    sla_project_count: int


class DashboardProjectMonthlyKpisResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectMonthlyKpiItemDTO]


class DashboardProjectComplexityCountItemDTO(BaseModel):
    project_type: str
    project_type_label: str
    complexity_score: int
    project_count: int


class DashboardProjectComplexityCountsResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectComplexityCountItemDTO]


class DashboardProjectComplexityByMonthItemDTO(BaseModel):
    project_type: str
    project_type_label: str
    responsible_login: str
    year: int
    month: int
    month_label: str
    period_label: str
    complexity_score: int
    project_count: int


class DashboardProjectComplexityByMonthResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectComplexityByMonthItemDTO]


class DashboardProjectEarnedValueItemDTO(BaseModel):
    project_id: int
    project_name: str
    project_type: str
    project_type_label: str
    responsible_login: str
    year: int
    month: int
    month_label: str
    period_label: str
    estimated_cost: float
    planned_value: float
    earned_value: float
    total_task_cost: float
    task_count: int
    completed_task_count: int


class DashboardProjectEarnedValueResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectEarnedValueItemDTO]


class DashboardProjectEffortDeviationItemDTO(BaseModel):
    project_type: str
    project_type_label: str
    responsible_login: str
    year: int
    month: int
    month_label: str
    period_label: str
    task_count: int
    planned_effort_hours: float
    actual_effort_hours: float
    effort_deviation_hours: float


class DashboardProjectEffortDeviationResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectEffortDeviationItemDTO]
