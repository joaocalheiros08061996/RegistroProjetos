from fastapi import APIRouter, Depends

from api.deps import AuthenticatedUser, get_dashboard_service, require_permission
from api.dtos import (
    DashboardAvgPlannedVsRealDaysByTypeResponseDTO,
    DashboardAvgRealDaysByTypeResponseDTO,
    DashboardNewProcessTimeByMonthResponseDTO,
    DashboardProjectComplexityByMonthResponseDTO,
    DashboardProjectComplexityCountsResponseDTO,
    DashboardProjectEffortDeviationResponseDTO,
    DashboardProjectEarnedValueResponseDTO,
    DashboardProjectMonthlyKpisResponseDTO,
    DashboardProjectsByResponsibleResponseDTO,
    DashboardRoutineTotalDaysByMonthResponseDTO,
)
from application.services import DashboardService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/avg-real-days-by-project-type",
    response_model=DashboardAvgRealDaysByTypeResponseDTO,
)
def get_avg_real_days_by_project_type(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "avg_real_days_by_project_type",
        "items": service.list_avg_real_days_by_project_type(),
    }


@router.get(
    "/avg-planned-vs-real-days-by-project-type",
    response_model=DashboardAvgPlannedVsRealDaysByTypeResponseDTO,
)
def get_avg_planned_vs_real_days_by_project_type(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "avg_planned_vs_real_days_by_project_type",
        "items": service.list_avg_planned_vs_real_days_by_project_type(),
    }


@router.get(
    "/routine-total-days-by-month",
    response_model=DashboardRoutineTotalDaysByMonthResponseDTO,
)
def get_routine_total_days_by_month(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "routine_total_days_by_month",
        "items": service.list_routine_total_days_by_month(),
    }


@router.get(
    "/new-process-time-by-month",
    response_model=DashboardNewProcessTimeByMonthResponseDTO,
)
def get_new_process_time_by_month(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "new_process_time_by_month",
        "items": service.list_new_process_time_by_month(),
    }


@router.get(
    "/project-monthly-kpis",
    response_model=DashboardProjectMonthlyKpisResponseDTO,
)
def get_project_monthly_kpis(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_monthly_kpis",
        "items": service.list_project_monthly_kpis(),
    }


@router.get(
    "/project-complexity-counts",
    response_model=DashboardProjectComplexityCountsResponseDTO,
)
def get_project_complexity_counts(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_complexity_counts",
        "items": service.list_project_complexity_counts(),
    }


@router.get(
    "/project-complexity-counts-by-month",
    response_model=DashboardProjectComplexityByMonthResponseDTO,
)
def get_project_complexity_counts_by_month(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_complexity_counts_by_month",
        "items": service.list_project_complexity_counts_by_month(),
    }


@router.get(
    "/projects-by-responsible",
    response_model=DashboardProjectsByResponsibleResponseDTO,
)
def get_projects_by_responsible(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "projects_by_responsible",
        "items": service.list_projects_by_responsible(),
    }


@router.get(
    "/project-earned-value",
    response_model=DashboardProjectEarnedValueResponseDTO,
)
def get_project_earned_value(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_earned_value",
        "items": service.list_project_earned_value(),
    }


@router.get(
    "/project-effort-deviation",
    response_model=DashboardProjectEffortDeviationResponseDTO,
)
def get_project_effort_deviation(
    _: AuthenticatedUser = Depends(require_permission("dashboard:read_global")),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_effort_deviation",
        "items": service.list_project_effort_deviation(),
    }
