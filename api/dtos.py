from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from domain.enums import (
    ProjectType,
    Severity,
    Urgency,
    Trend,
    ObjectiveClarity,
    MethodClarity,
    ProcessClassification,
)
from domain.routine_activity import ROUTINE_ACTIVITY_TYPES
from domain.validation import (
    DESCRIPTION_MAX_LENGTH,
    FTE_MAX,
    FTE_MIN,
    MONEY_MAX,
    MONEY_MIN,
    PROJECT_NAME_MAX_LENGTH,
    RESPONSIBLE_MAX_LENGTH,
    TASK_NAME_MAX_LENGTH,
)


# ============================================================
# INPUT DTOS
# ============================================================


class StrictInputDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateProjectDTO(StrictInputDTO):
    """
    DTO de entrada para criação de um projeto.
    """

    name: str = Field(..., min_length=1, max_length=PROJECT_NAME_MAX_LENGTH)
    project_type: ProjectType
    responsible_login: str = Field(..., min_length=1, max_length=RESPONSIBLE_MAX_LENGTH)
    fte: float = Field(..., ge=FTE_MIN, le=FTE_MAX)

    planned_start: datetime
    planned_end: datetime

    # classificação GUT
    severity: Severity = Severity.NONE
    urgency: Urgency = Urgency.CAN_WAIT
    trend: Trend = Trend.STABLE

    # NOVOS CAMPOS
    objective_clarity: ObjectiveClarity = ObjectiveClarity.FULLY_DEFINED
    method_clarity: MethodClarity = MethodClarity.FULLY_DEFINED
    process_classification: Optional[ProcessClassification] = None

    estimated_cost: float = Field(default=0.0, ge=MONEY_MIN, le=MONEY_MAX)

    @field_validator("fte")
    @classmethod
    def validate_integer_fte(cls, value: float) -> float:
        if not float(value).is_integer():
            raise ValueError("FTE deve ser um numero inteiro.")
        return value


class CreateTaskDTO(StrictInputDTO):
    """
    DTO de entrada para criação de uma tarefa.
    """

    name: str = Field(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH)
    planned_start: datetime
    planned_end: datetime
    cost: float = Field(default=0.0, ge=MONEY_MIN, le=MONEY_MAX)


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
    process_classification: Optional[str] = None

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

    # complexidade
    complexity_score: int
    complexity_label: str


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
    process_classification: Optional[str] = None

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
    process_classification: Optional[str] = None

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

class StartRoutineActivityDTO(StrictInputDTO):
    tipo_atividade: str = Field(..., min_length=1, max_length=80)
    responsavel: str = Field(default="", max_length=RESPONSIBLE_MAX_LENGTH)
    descricao: str = Field(default="", max_length=DESCRIPTION_MAX_LENGTH)

    @field_validator("tipo_atividade")
    @classmethod
    def validate_tipo_atividade(cls, value: str) -> str:
        if value not in ROUTINE_ACTIVITY_TYPES:
            raise ValueError("Tipo de atividade invalido.")
        return value


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


class DashboardNewProcessTimeByMonthItemDTO(BaseModel):
    responsible_label: str
    year: int
    month: int
    month_label: str
    period_label: str
    project_days: float
    routine_days: float
    total_days: float


class DashboardNewProcessTimeByMonthResponseDTO(BaseModel):
    chart: str
    items: list[DashboardNewProcessTimeByMonthItemDTO]


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


class DashboardProjectsByResponsibleItemDTO(BaseModel):
    project_id: int
    project_name: str
    project_type: str
    project_type_label: str
    responsible_login: str
    planned_start: datetime
    planned_end: datetime
    estimated_cost: float
    task_count: int
    completed_task_count: int
    percent_completed: float
    gut_score: int
    priority_level: int
    priority_label: str
    complexity_score: int
    complexity_label: str
    year: int
    month: int
    month_label: str
    period_label: str


class DashboardProjectsByResponsibleResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectsByResponsibleItemDTO]


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
    planned_effort_hours: float
    actual_effort_hours: float
    planned_labor_cost: float
    actual_labor_cost: float
    actual_cost: float
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
    planned_labor_cost: float
    actual_labor_cost: float
    labor_cost_deviation: float


class DashboardProjectEffortDeviationResponseDTO(BaseModel):
    chart: str
    items: list[DashboardProjectEffortDeviationItemDTO]
