from fastapi import APIRouter, Depends

from api.deps import get_current_user_id, get_dashboard_service
from api.dtos import (
    DashboardAvgPlannedVsRealDaysByTypeResponseDTO,
    DashboardAvgRealDaysByTypeResponseDTO,
    DashboardProjectComplexityByMonthResponseDTO,
    DashboardProjectComplexityCountsResponseDTO,
    DashboardProjectEffortDeviationResponseDTO,
    DashboardProjectEarnedValueResponseDTO,
    DashboardProjectMonthlyKpisResponseDTO,
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
    _: str = Depends(get_current_user_id),
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
    _: str = Depends(get_current_user_id),
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
    _: str = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "routine_total_days_by_month",
        "items": service.list_routine_total_days_by_month(),
    }


@router.get(
    "/project-monthly-kpis",
    response_model=DashboardProjectMonthlyKpisResponseDTO,
)
def get_project_monthly_kpis(
    _: str = Depends(get_current_user_id),
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
    _: str = Depends(get_current_user_id),
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
    _: str = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_complexity_counts_by_month",
        "items": service.list_project_complexity_counts_by_month(),
    }


@router.get(
    "/project-earned-value",
    response_model=DashboardProjectEarnedValueResponseDTO,
)
def get_project_earned_value(
    _: str = Depends(get_current_user_id),
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
    _: str = Depends(get_current_user_id),
    service: DashboardService = Depends(get_dashboard_service),
):
    return {
        "chart": "project_effort_deviation",
        "items": service.list_project_effort_deviation(),
    }
