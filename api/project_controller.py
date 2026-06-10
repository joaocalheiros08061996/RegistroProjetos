from fastapi import APIRouter, Depends, Path

from application.services import ProjectService
from api.dtos import (
    CreateProjectDTO,
    ProjectDetailResponseDTO,
    ProjectListItemResponseDTO,
    ProjectSummaryResponseDTO,
    ProjectMetricsResponseDTO,
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
        description=dto.description,
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
        process_classification=dto.process_classification,

        estimated_cost=dto.estimated_cost,
    )

    return ProjectSummaryResponseDTO(
        id=project.id,
        name=project.name,
        description=project.description,
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
    projects = service.list_project_summaries_for_user(user_id)
    return [ProjectListItemResponseDTO(**project) for project in projects]


# ------------------------------------------------------------------
# Delete Project
# ------------------------------------------------------------------

@router.delete("/{project_id}")
def delete_project(
    project_id: int = Path(..., gt=0),
    service: ProjectService = Depends(get_project_service),
    user_id: str = Depends(get_current_user_id),
):
    service.delete_project(project_id, user_id)
    return {"status": "deleted"}


# ------------------------------------------------------------------
# Project Metrics
# ------------------------------------------------------------------

@router.get("/{project_id}", response_model=ProjectMetricsResponseDTO)
def get_project_metrics(
    project_id: int = Path(..., gt=0),
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
    project_id: int = Path(..., gt=0),
    service: ProjectService = Depends(get_project_service),
    user_id: str = Depends(get_current_user_id),
):
    detail = service.get_project_detail(project_id, user_id)
    return ProjectDetailResponseDTO(**detail)
