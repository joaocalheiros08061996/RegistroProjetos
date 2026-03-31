from fastapi import APIRouter, Depends

from application.services import ProjectService
from api.dtos import (
    CreateProjectDTO,
    ProjectDetailResponseDTO,
    ProjectListItemResponseDTO,
    ProjectSummaryResponseDTO,
    ProjectMetricsResponseDTO,
    TaskResponseDTO,
)
from api.deps import get_project_service, get_current_user_id

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

# ------------------------------------------------------------------
# Create Project
# ------------------------------------------------------------------

@router.post("/", response_model=ProjectSummaryResponseDTO)
def create_project(
    dto: CreateProjectDTO,
    service: ProjectService = Depends(get_project_service),
    user_id: str = Depends(get_current_user_id),
):
    project = service.create_project(
        user_id=user_id,
        name=dto.name,
        project_type=dto.project_type,
        responsible_login=dto.responsible_login,
        fte=dto.fte,
        planned_start=dto.planned_start,
        planned_end=dto.planned_end,

        # classificação GUT
        severity=dto.severity,
        urgency=dto.urgency,
        trend=dto.trend,

        # novos campos
        objective_clarity=dto.objective_clarity,
        method_clarity=dto.method_clarity,

        estimated_cost=dto.estimated_cost,
    )

    return ProjectSummaryResponseDTO(
        id=project.id,
        name=project.name,
        task_count=project.task_count,
    )


# ------------------------------------------------------------------
# List Projects
# ------------------------------------------------------------------

@router.get("/", response_model=list[ProjectListItemResponseDTO])
def list_projects(
    service: ProjectService = Depends(get_project_service),
    user_id: str = Depends(get_current_user_id),
):
    projects = service.list_projects_for_user(user_id)

    return [
        ProjectListItemResponseDTO(
            id=project.id,
            name=project.name,
            project_type=project.project_type.value,
            responsible_login=project.responsible_login,
            planned_start=project.planned_start,
            planned_end=project.planned_end,
            estimated_cost=project.estimated_cost,
            task_count=project.task_count,
            percent_completed=project.percent_completed,
        )
        for project in projects
    ]


# ------------------------------------------------------------------
# Project Metrics
# ------------------------------------------------------------------

@router.get("/{project_id}", response_model=ProjectMetricsResponseDTO)
def get_project_metrics(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    user_id: str = Depends(get_current_user_id),
):
    metrics = service.get_project_metrics(project_id, user_id)

    return ProjectMetricsResponseDTO(
        percent_completed=metrics["percent_completed"],
        actual_days=metrics["actual_days"],
        task_count=metrics["task_count"],
        active_tasks=metrics["active_tasks"],
    )


# ------------------------------------------------------------------
# Project Detail
# ------------------------------------------------------------------

@router.get("/{project_id}/detail", response_model=ProjectDetailResponseDTO)
def get_project_detail(
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    user_id: str = Depends(get_current_user_id),
):
    project = service.get_project(project_id, user_id)
    tasks = project.list_tasks()

    return ProjectDetailResponseDTO(
        id=project.id,
        name=project.name,
        project_type=project.project_type.value,
        responsible_login=project.responsible_login,
        fte=project.fte,
        planned_start=project.planned_start,
        planned_end=project.planned_end,

        # classificação GUT
        severity=project.severity.value,
        urgency=project.urgency.value,
        trend=project.trend.value,

        # novos campos
        objective_clarity=project.objective_clarity.value,
        method_clarity=project.method_clarity.value,

        estimated_cost=project.estimated_cost,

        # métricas
        task_count=project.task_count,
        percent_completed=project.percent_completed,
        actual_days=project.actual_days(),

        active_tasks=[t.name for t in project.active_tasks()],

        tasks=[
            TaskResponseDTO(
                name=task.name,
                status=task.status.value,
                planned_start=task.planned_start,
                planned_end=task.planned_end,
                cost=task.cost,
                actual_seconds=round(task.actual_time.total_seconds(), 2),
                time_entries_count=len(task.time_entries),
                percent_completed=task.percent_completed,
            )
            for task in tasks
        ],
    )
