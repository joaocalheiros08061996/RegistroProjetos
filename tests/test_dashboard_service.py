from datetime import datetime, timezone
from datetime import timedelta
from math import isclose

from application.services import DashboardService
from domain.constants import ENGINEERING_PROCESS_HOURLY_RATE, WORKDAY_HOURS
from domain.entities import Project
from domain.enums import MethodClarity, ObjectiveClarity, ProcessClassification, ProjectType
from domain.routine_activity import RoutineActivity
from domain.work_schedule import planned_interval_to_hours
from infra.in_memory_repos import (
    InMemoryDashboardRepository,
    InMemoryProjectRepository,
    InMemoryRoutineActivityRepository,
)


def _build_project(
    *,
    user_id: str,
    name: str,
    project_type: ProjectType,
    responsible_login: str = "user",
    planned_start: datetime = datetime(2026, 1, 1),
    planned_end: datetime = datetime(2026, 1, 31),
    objective_clarity=ObjectiveClarity.FULLY_DEFINED,
    method_clarity=MethodClarity.FULLY_DEFINED,
    process_classification: ProcessClassification | None = None,
    estimated_cost: float = 0.0,
) -> Project:
    return Project(
        user_id=user_id,
        name=name,
        project_type=project_type,
        responsible_login=responsible_login,
        fte=1.0,
        planned_start=planned_start,
        planned_end=planned_end,
        objective_clarity=objective_clarity,
        method_clarity=method_clarity,
        process_classification=process_classification,
        estimated_cost=estimated_cost,
    )


def test_dashboard_service_returns_global_average_and_ignores_open_entries():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    project_1 = _build_project(user_id="u1", name="Projeto U1", project_type=ProjectType.LAYOUT)
    project_2 = _build_project(user_id="u2", name="Projeto U2", project_type=ProjectType.LAYOUT)
    project_3 = _build_project(user_id="u3", name="Projeto Open", project_type=ProjectType.EXPORTACAO)

    project_repo.save(project_1)
    project_repo.save(project_2)
    project_repo.save(project_3)

    task_1 = project_1.start_new_task("task-1", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_1.add_manual_entry(datetime(2026, 1, 1, 8, 0, 0), datetime(2026, 1, 3, 8, 0, 0))  # 2 dias

    task_2 = project_2.start_new_task("task-2", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_2.add_manual_entry(datetime(2026, 1, 4, 8, 0, 0), datetime(2026, 1, 8, 8, 0, 0))  # 4 dias

    task_3 = project_3.start_new_task("task-3", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_3.start(datetime(2026, 1, 10, 8, 0, 0))  # entrada aberta: deve ser ignorada

    items = service.list_avg_real_days_by_project_type()

    assert len(items) == 1
    assert items[0]["project_type"] == "LAYOUT"
    assert items[0]["project_type_label"] == "LAYOUT"
    assert isclose(items[0]["average_days"], 72.0 / 24.0, rel_tol=0, abs_tol=1e-10)


def test_dashboard_service_sorts_descending_and_applies_labels():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    project_a = _build_project(user_id="u1", name="Projeto A", project_type=ProjectType.NORMATIZACAO)
    project_b = _build_project(user_id="u2", name="Projeto B", project_type=ProjectType.PADRONIZACAO)

    project_repo.save(project_a)
    project_repo.save(project_b)

    task_a = project_a.start_new_task("task-a", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_a.add_manual_entry(datetime(2026, 1, 1, 8, 0, 0), datetime(2026, 1, 6, 8, 0, 0))  # 5 dias

    task_b = project_b.start_new_task("task-b", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_b.add_manual_entry(datetime(2026, 1, 1, 8, 0, 0), datetime(2026, 1, 3, 8, 0, 0))  # 2 dias

    items = service.list_avg_real_days_by_project_type()

    assert [item["project_type"] for item in items] == ["NORMATIZACAO", "PADRONIZACAO"]
    assert items[0]["project_type_label"] == "NORMATIZAÇÃO"
    assert items[1]["project_type_label"] == "PADRONIZAÇÃO"


def test_dashboard_service_keeps_small_non_zero_values():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    project_norm = _build_project(
        user_id="u1",
        name="Projeto N",
        project_type=ProjectType.NORMATIZACAO,
    )
    project_map = _build_project(
        user_id="u2",
        name="Projeto M",
        project_type=ProjectType.MAPEAMENTO,
    )

    project_repo.save(project_norm)
    project_repo.save(project_map)

    tiny_task = project_norm.start_new_task("tiny-task", datetime(2026, 1, 1), datetime(2026, 1, 2))
    tiny_task.add_manual_entry(
        datetime(2026, 1, 1, 8, 0, 0),
        datetime(2026, 1, 1, 8, 2, 7),  # 00:02:07
    )

    map_task = project_map.start_new_task("map-task", datetime(2026, 1, 1), datetime(2026, 1, 2))
    map_task.add_manual_entry(
        datetime(2026, 1, 1, 8, 0, 0),
        datetime(2026, 1, 14, 3, 27, 44),  # 307:27:44
    )

    items = service.list_avg_real_days_by_project_type()

    assert [item["project_type"] for item in items] == ["MAPEAMENTO", "NORMATIZACAO"]

    map_value = next(item["average_days"] for item in items if item["project_type"] == "MAPEAMENTO")
    norm_value = next(item["average_days"] for item in items if item["project_type"] == "NORMATIZACAO")

    assert isclose(map_value, (307.0 + 27.0 / 60.0 + 44.0 / 3600.0) / 24.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(norm_value, 127.0 / 86400.0, rel_tol=0, abs_tol=1e-10)


def test_dashboard_service_returns_planned_vs_real_averages():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    project_1 = _build_project(user_id="u1", name="Projeto 1", project_type=ProjectType.LAYOUT)
    project_2 = _build_project(user_id="u2", name="Projeto 2", project_type=ProjectType.LAYOUT)
    project_1.planned_start = datetime(2026, 1, 1, 8, 0, 0)
    project_1.planned_end = datetime(2026, 1, 11, 8, 0, 0)  # 10 dias
    project_2.planned_start = datetime(2026, 1, 1, 8, 0, 0)
    project_2.planned_end = datetime(2026, 1, 9, 8, 0, 0)   # 8 dias

    project_repo.save(project_1)
    project_repo.save(project_2)

    task_1 = project_1.start_new_task("task-1", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_1.add_manual_entry(datetime(2026, 1, 1, 8, 0, 0), datetime(2026, 1, 3, 8, 0, 0))  # 2 dias

    task_2 = project_2.start_new_task("task-2", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_2.add_manual_entry(datetime(2026, 1, 4, 8, 0, 0), datetime(2026, 1, 8, 8, 0, 0))  # 4 dias

    items = service.list_avg_planned_vs_real_days_by_project_type()
    assert len(items) == 1
    assert items[0]["project_type"] == "LAYOUT"
    assert isclose(items[0]["planned_average_days"], 9.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(items[0]["real_average_days"], 72.0 / 24.0, rel_tol=0, abs_tol=1e-10)


def test_dashboard_service_returns_project_monthly_kpis_by_responsible():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    project_1 = _build_project(
        user_id="u1",
        name="Layout Jan",
        project_type=ProjectType.LAYOUT,
        responsible_login="ana",
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 1, 11),  # 10 dias
    )
    project_2 = _build_project(
        user_id="u2",
        name="Layout Jan 2",
        project_type=ProjectType.LAYOUT,
        responsible_login="ana",
        planned_start=datetime(2026, 1, 5),
        planned_end=datetime(2026, 1, 25),  # 20 dias
    )
    project_3 = _build_project(
        user_id="u3",
        name="Map Fev",
        project_type=ProjectType.MAPEAMENTO,
        responsible_login="bruno",
        planned_start=datetime(2026, 2, 1),
        planned_end=datetime(2026, 2, 6),  # 5 dias
    )
    project_4 = _build_project(
        user_id="u4",
        name="Sem Real",
        project_type=ProjectType.MELHORIA,
        responsible_login="ana",
        planned_start=datetime(2026, 3, 1),
        planned_end=datetime(2026, 3, 6),  # 5 dias
    )

    project_repo.save(project_1)
    project_repo.save(project_2)
    project_repo.save(project_3)
    project_repo.save(project_4)

    task_1 = project_1.start_new_task("task-1", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_1.add_manual_entry(datetime(2026, 1, 1), datetime(2026, 1, 13))  # 12 dias, estourou

    task_2 = project_2.start_new_task("task-2", datetime(2026, 1, 1), datetime(2026, 1, 2))
    task_2.add_manual_entry(datetime(2026, 1, 1), datetime(2026, 1, 11))  # 10 dias, nao estourou
    task_2.start(datetime(2026, 1, 20))  # aberta: deve ser ignorada

    task_3 = project_3.start_new_task("task-3", datetime(2026, 2, 1), datetime(2026, 2, 2))
    task_3.add_manual_entry(datetime(2026, 2, 1), datetime(2026, 2, 4))  # 3 dias

    items = service.list_project_monthly_kpis()

    layout_jan = next(
        item
        for item in items
        if item["project_type"] == "LAYOUT"
        and item["responsible_login"] == "Ana"
        and item["year"] == 2026
        and item["month"] == 1
    )
    assert layout_jan["project_type_label"] == "LAYOUT"
    assert layout_jan["month_label"] == "JAN"
    assert layout_jan["period_label"] == "JAN 2026"
    assert layout_jan["project_count"] == 2
    assert isclose(layout_jan["planned_days_sum"], 30.0, rel_tol=0, abs_tol=1e-10)
    assert layout_jan["planned_days_count"] == 2
    assert isclose(layout_jan["real_days_sum"], 22.0, rel_tol=0, abs_tol=1e-10)
    assert layout_jan["real_days_count"] == 2
    assert layout_jan["sla_breach_count"] == 1
    assert layout_jan["sla_project_count"] == 2

    map_fev = next(item for item in items if item["project_type"] == "MAPEAMENTO")
    assert map_fev["responsible_login"] == "Bruno"
    assert map_fev["month_label"] == "FEV"
    assert map_fev["project_count"] == 1
    assert isclose(map_fev["planned_days_sum"], 5.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(map_fev["real_days_sum"], 3.0, rel_tol=0, abs_tol=1e-10)
    assert map_fev["sla_breach_count"] == 0

    no_real = next(item for item in items if item["project_type"] == "MELHORIA")
    assert no_real["project_type_label"] == "MELHORIA DE PROC. EXISTENTES"
    assert no_real["responsible_login"] == "Ana"
    assert no_real["project_count"] == 1
    assert no_real["planned_days_sum"] == 0.0
    assert no_real["planned_days_count"] == 0
    assert no_real["real_days_sum"] == 0.0
    assert no_real["real_days_count"] == 0
    assert no_real["sla_project_count"] == 0


def test_dashboard_service_returns_project_complexity_counts():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    layout_low = _build_project(
        user_id="u1",
        name="Layout Baixa",
        project_type=ProjectType.LAYOUT,
        objective_clarity=ObjectiveClarity.FULLY_DEFINED,
        method_clarity=MethodClarity.PARTIALLY_KNOWN,
    )  # 1 * 3 = 3 => Complexidade 1
    layout_high = _build_project(
        user_id="u2",
        name="Layout Alta",
        project_type=ProjectType.LAYOUT,
        objective_clarity=ObjectiveClarity.CLEAR_WITH_AMBIGUITIES,
        method_clarity=MethodClarity.POORLY_DEFINED,
    )  # 2 * 4 = 8 => Complexidade 2
    layout_high_2 = _build_project(
        user_id="u3",
        name="Layout Alta 2",
        project_type=ProjectType.LAYOUT,
        objective_clarity="CLEAR_WITH_AMBIGUITIES",
        method_clarity="POORLY_DEFINED",
    )  # valores legados: 2 * 4 = 8 => Complexidade 2
    mapping_max = _build_project(
        user_id="u4",
        name="Mapeamento Max",
        project_type=ProjectType.MAPEAMENTO,
        objective_clarity="UNDEFINED",
        method_clarity="UNKNOWN",
    )  # valores legados: 5 * 5 = 25 => Complexidade 5
    ignored = _build_project(
        user_id="u5",
        name="Ignorado",
        project_type=ProjectType.EXPORTACAO,
        objective_clarity="INVALID",
        method_clarity=MethodClarity.FULLY_DEFINED,
    )

    for project in [layout_low, layout_high, layout_high_2, mapping_max, ignored]:
        project_repo.save(project)

    items = service.list_project_complexity_counts()

    assert items == [
        {
            "project_type": "LAYOUT",
            "project_type_label": "LAYOUT",
            "complexity_score": 1,
            "project_count": 1,
        },
        {
            "project_type": "LAYOUT",
            "project_type_label": "LAYOUT",
            "complexity_score": 2,
            "project_count": 2,
        },
        {
            "project_type": "MAPEAMENTO",
            "project_type_label": "MAPEAMENTO",
            "complexity_score": 5,
            "project_count": 1,
        },
    ]


def test_dashboard_service_returns_project_complexity_counts_by_month_with_filter_dimensions():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    layout_jan = _build_project(
        user_id="u1",
        name="Layout Jan",
        project_type=ProjectType.LAYOUT,
        responsible_login="ana",
        planned_start=datetime(2026, 1, 10),
        objective_clarity=ObjectiveClarity.FULLY_DEFINED,
        method_clarity=MethodClarity.PARTIALLY_KNOWN,
    )  # 1 * 3 = 3 => Complexidade 1
    layout_jan_legacy = _build_project(
        user_id="u2",
        name="Layout Jan Legacy",
        project_type=ProjectType.LAYOUT,
        responsible_login="bruno",
        planned_start=datetime(2026, 1, 15),
        objective_clarity="CLEAR_WITH_AMBIGUITIES",
        method_clarity="POORLY_DEFINED",
    )  # valores legados: 2 * 4 = 8 => Complexidade 2
    norm_jan = _build_project(
        user_id="u3",
        name="Norm Jan",
        project_type=ProjectType.NORMATIZACAO,
        responsible_login="ana",
        planned_start=datetime(2026, 1, 20),
        objective_clarity=ObjectiveClarity.CLEAR_WITH_AMBIGUITIES,
        method_clarity=MethodClarity.POORLY_DEFINED,
    )  # 2 * 4 = 8 => Complexidade 2
    map_fev = _build_project(
        user_id="u4",
        name="Map Fev",
        project_type=ProjectType.MAPEAMENTO,
        responsible_login="bruno",
        planned_start=datetime(2026, 2, 1),
        planned_end=datetime(2026, 2, 28),
        objective_clarity="UNDEFINED",
        method_clarity="UNKNOWN",
    )  # valores legados: 5 * 5 = 25 => Complexidade 5
    ignored = _build_project(
        user_id="u5",
        name="Ignorado",
        project_type=ProjectType.EXPORTACAO,
        responsible_login="ana",
        planned_start=datetime(2026, 1, 8),
        objective_clarity="INVALID",
        method_clarity=MethodClarity.FULLY_DEFINED,
    )

    for project in [layout_jan, layout_jan_legacy, norm_jan, map_fev, ignored]:
        project_repo.save(project)

    items = service.list_project_complexity_counts_by_month()

    assert items == [
        {
            "project_type": "LAYOUT",
            "project_type_label": "LAYOUT",
            "responsible_login": "Ana",
            "year": 2026,
            "month": 1,
            "month_label": "JAN",
            "period_label": "JAN 2026",
            "complexity_score": 1,
            "project_count": 1,
        },
        {
            "project_type": "LAYOUT",
            "project_type_label": "LAYOUT",
            "responsible_login": "Bruno",
            "year": 2026,
            "month": 1,
            "month_label": "JAN",
            "period_label": "JAN 2026",
            "complexity_score": 2,
            "project_count": 1,
        },
        {
            "project_type": "NORMATIZACAO",
            "project_type_label": "NORMATIZAÇÃO",
            "responsible_login": "Ana",
            "year": 2026,
            "month": 1,
            "month_label": "JAN",
            "period_label": "JAN 2026",
            "complexity_score": 2,
            "project_count": 1,
        },
        {
            "project_type": "MAPEAMENTO",
            "project_type_label": "MAPEAMENTO",
            "responsible_login": "Bruno",
            "year": 2026,
            "month": 2,
            "month_label": "FEV",
            "period_label": "FEV 2026",
            "complexity_score": 5,
            "project_count": 1,
        },
    ]


def test_dashboard_service_returns_project_earned_value_by_period_and_responsible():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)
    now = datetime.now()

    project_done = _build_project(
        user_id="u1",
        name="Projeto Encerrado",
        project_type=ProjectType.LAYOUT,
        responsible_login="ana",
        planned_start=now - timedelta(days=20),
        planned_end=now - timedelta(days=10),
        estimated_cost=1000.0,
    )
    project_future = _build_project(
        user_id="u2",
        name="Projeto Futuro",
        project_type=ProjectType.MAPEAMENTO,
        responsible_login="bruno",
        planned_start=now + timedelta(days=5),
        planned_end=now + timedelta(days=15),
        estimated_cost=800.0,
    )
    project_fallback_budget = _build_project(
        user_id="u3",
        name="Projeto Sem Estimado",
        project_type=ProjectType.NORMATIZACAO,
        responsible_login="ana",
        planned_start=now - timedelta(days=10),
        planned_end=now - timedelta(days=1),
        estimated_cost=0.0,
    )

    for project in [project_done, project_future, project_fallback_budget]:
        project_repo.save(project)

    done_task_1 = project_done.start_new_task("Entrega A", now - timedelta(days=19), now - timedelta(days=18), cost=400.0)
    done_task_1.mark_completed()
    done_task_2 = project_done.start_new_task("Entrega B", now - timedelta(days=18), now - timedelta(days=17), cost=200.0)
    done_task_2.mark_completed()
    project_done.start_new_task("Entrega C", now - timedelta(days=17), now - timedelta(days=16), cost=300.0)

    future_task = project_future.start_new_task("Entrega futura", now + timedelta(days=6), now + timedelta(days=8), cost=300.0)
    future_task.mark_completed()

    fallback_task = project_fallback_budget.start_new_task("Entrega norm", now - timedelta(days=9), now - timedelta(days=8), cost=250.0)
    fallback_task.mark_completed()

    items = service.list_project_earned_value()

    done_item = next(item for item in items if item["project_name"] == "Projeto Encerrado")
    done_planned_hours = sum(
        planned_interval_to_hours(task.planned_start, task.planned_end)
        for task in project_done.list_tasks()
    )
    done_completed_hours = sum(
        planned_interval_to_hours(task.planned_start, task.planned_end)
        for task in project_done.completed_tasks()
    )
    done_planned_labor = done_planned_hours * ENGINEERING_PROCESS_HOURLY_RATE
    done_completed_labor = done_completed_hours * ENGINEERING_PROCESS_HOURLY_RATE
    assert done_item["project_type"] == "LAYOUT"
    assert done_item["project_type_label"] == "LAYOUT"
    assert done_item["responsible_login"] == "Ana"
    assert done_item["month_label"] in service._MONTH_LABELS.values()
    assert done_item["period_label"] == f'{done_item["month_label"]} {done_item["year"]}'
    assert done_item["estimated_cost"] == 1000.0
    assert isclose(done_item["planned_value"], 1000.0 + done_planned_labor, rel_tol=0, abs_tol=1e-10)
    assert isclose(done_item["earned_value"], 600.0 + done_completed_labor, rel_tol=0, abs_tol=1e-10)
    assert done_item["total_task_cost"] == 900.0
    assert isclose(done_item["planned_effort_hours"], done_planned_hours, rel_tol=0, abs_tol=1e-10)
    assert isclose(done_item["actual_effort_hours"], 0.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(done_item["planned_labor_cost"], done_planned_labor, rel_tol=0, abs_tol=1e-10)
    assert isclose(done_item["actual_labor_cost"], 0.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(done_item["actual_cost"], 900.0, rel_tol=0, abs_tol=1e-10)
    assert done_item["task_count"] == 3
    assert done_item["completed_task_count"] == 2
    assert "schedule_performance_index" not in done_item

    future_item = next(item for item in items if item["project_name"] == "Projeto Futuro")
    future_completed_hours = planned_interval_to_hours(
        future_task.planned_start,
        future_task.planned_end,
    )
    future_completed_labor = future_completed_hours * ENGINEERING_PROCESS_HOURLY_RATE
    assert future_item["planned_value"] == 0.0
    assert isclose(future_item["earned_value"], 300.0 + future_completed_labor, rel_tol=0, abs_tol=1e-10)
    assert "schedule_performance_index" not in future_item

    fallback_item = next(item for item in items if item["project_name"] == "Projeto Sem Estimado")
    fallback_hours = planned_interval_to_hours(
        fallback_task.planned_start,
        fallback_task.planned_end,
    )
    fallback_labor = fallback_hours * ENGINEERING_PROCESS_HOURLY_RATE
    assert fallback_item["estimated_cost"] == 0.0
    assert isclose(fallback_item["planned_value"], 250.0 + fallback_labor, rel_tol=0, abs_tol=1e-10)
    assert isclose(fallback_item["earned_value"], 250.0 + fallback_labor, rel_tol=0, abs_tol=1e-10)
    assert isclose(fallback_item["actual_cost"], 250.0, rel_tol=0, abs_tol=1e-10)
    assert fallback_item["project_type_label"] == "NORMATIZAÇÃO"
    assert "schedule_performance_index" not in fallback_item


def test_dashboard_service_returns_project_effort_deviation_by_period_and_responsible():
    project_repo = InMemoryProjectRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo)
    service = DashboardService(dashboard_repo)

    project = _build_project(
        user_id="u1",
        name="Projeto Esforço",
        project_type=ProjectType.LAYOUT,
        responsible_login="ana",
        planned_start=datetime(2026, 5, 1),
        planned_end=datetime(2026, 5, 30),
    )
    ignored_project = _build_project(
        user_id="u2",
        name="Projeto Aberto",
        project_type=ProjectType.NORMATIZACAO,
        responsible_login="bruno",
        planned_start=datetime(2026, 5, 1),
        planned_end=datetime(2026, 5, 30),
    )

    project_repo.save(project)
    project_repo.save(ignored_project)

    task_a = project.start_new_task(
        "Entrega A",
        datetime(2026, 5, 4, 8, 0),
        datetime(2026, 5, 4, 16, 0),  # 8h planejadas
    )
    task_a.add_manual_entry(
        datetime(2026, 5, 4, 8, 0),
        datetime(2026, 5, 4, 18, 0),  # 10h reais
    )

    task_b = project.start_new_task(
        "Entrega B",
        datetime(2026, 5, 5, 8, 0),
        datetime(2026, 5, 5, 12, 0),  # 4h planejadas
    )
    task_b.add_manual_entry(
        datetime(2026, 5, 5, 8, 0),
        datetime(2026, 5, 5, 11, 0),  # 3h reais
    )

    open_task = ignored_project.start_new_task(
        "Entrega aberta",
        datetime(2026, 5, 6, 8, 0),
        datetime(2026, 5, 6, 12, 0),
    )
    open_task.start(datetime(2026, 5, 6, 8, 0))  # entrada aberta: deve ser ignorada

    items = service.list_project_effort_deviation()

    assert len(items) == 1
    item = items[0]
    assert item["project_type"] == "LAYOUT"
    assert item["project_type_label"] == "LAYOUT"
    assert item["responsible_login"] == "Ana"
    assert item["year"] == 2026
    assert item["month"] == 5
    assert item["month_label"] == "MAI"
    assert item["period_label"] == "MAI 2026"
    assert item["task_count"] == 2
    assert isclose(item["planned_effort_hours"], 12.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(item["actual_effort_hours"], 13.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(item["effort_deviation_hours"], 1.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(
        item["planned_labor_cost"],
        12.0 * ENGINEERING_PROCESS_HOURLY_RATE,
        rel_tol=0,
        abs_tol=1e-10,
    )
    assert isclose(
        item["actual_labor_cost"],
        13.0 * ENGINEERING_PROCESS_HOURLY_RATE,
        rel_tol=0,
        abs_tol=1e-10,
    )
    assert isclose(
        item["labor_cost_deviation"],
        ENGINEERING_PROCESS_HOURLY_RATE,
        rel_tol=0,
        abs_tol=1e-10,
    )


def test_dashboard_service_returns_routine_total_days_by_month():
    project_repo = InMemoryProjectRepository()
    routine_repo = InMemoryRoutineActivityRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo, routine_repo)
    service = DashboardService(dashboard_repo)

    routine_repo.save(
        RoutineActivity(
            user_id="u1",
            responsavel="Ana",
            tipo_atividade="Cadastro",
            inicio=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 1, 10, 20, 0, tzinfo=timezone.utc),
            horas_trabalhadas=12.0,
        )
    )
    routine_repo.save(
        RoutineActivity(
            user_id="u2",
            responsavel="Bruno",
            tipo_atividade="Cadastro",
            inicio=datetime(2026, 1, 11, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 1, 11, 20, 0, tzinfo=timezone.utc),
            horas_trabalhadas=12.0,
        )
    )
    routine_repo.save(
        RoutineActivity(
            user_id="36f1e40c-949e-4850-b86d-607dc6a468d3",
            tipo_atividade="Reuniões",
            inicio=datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 2, 2, 8, 0, tzinfo=timezone.utc),
            horas_trabalhadas=24.0,
        )
    )
    routine_repo.save(
        RoutineActivity(
            user_id="u4",
            tipo_atividade="Reuniões",
            inicio=datetime(2026, 2, 3, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 2, 4, 8, 0, tzinfo=timezone.utc),
            horas_trabalhadas=None,
        )
    )

    items = service.list_routine_total_days_by_month()

    assert len(items) == 4
    assert items[0]["user_id"] == "u1"
    assert items[0]["user_label"] == "Ana"
    assert items[0]["activity_type"] == "Cadastro"
    assert items[0]["year"] == 2026
    assert items[0]["month"] == 1
    assert items[0]["month_label"] == "JAN"
    assert items[0]["period_label"] == "JAN 2026"
    assert isclose(items[0]["total_days"], 12.0 / WORKDAY_HOURS, rel_tol=0, abs_tol=1e-10)

    assert items[1]["user_id"] == "u2"
    assert items[1]["user_label"] == "Bruno"
    assert items[1]["activity_type"] == "Cadastro"
    assert items[1]["month_label"] == "JAN"
    assert isclose(items[1]["total_days"], 12.0 / WORKDAY_HOURS, rel_tol=0, abs_tol=1e-10)

    assert items[2]["user_id"] == "36f1e40c-949e-4850-b86d-607dc6a468d3"
    assert items[2]["user_label"] == "Usuário 36f1...68d3"
    assert items[2]["activity_type"] == "Reuniões"
    assert items[2]["month_label"] == "FEV"
    assert isclose(items[2]["total_days"], 24.0 / WORKDAY_HOURS, rel_tol=0, abs_tol=1e-10)

    assert items[3]["user_id"] == "u4"
    assert items[3]["user_label"] == "u4"
    assert items[3]["activity_type"] == "Reuniões"
    assert items[3]["month_label"] == "FEV"
    assert isclose(items[3]["total_days"], 24.0 / WORKDAY_HOURS, rel_tol=0, abs_tol=1e-10)


def test_dashboard_service_returns_new_process_time_by_month():
    project_repo = InMemoryProjectRepository()
    routine_repo = InMemoryRoutineActivityRepository()
    dashboard_repo = InMemoryDashboardRepository(project_repo, routine_repo)
    service = DashboardService(dashboard_repo)

    new_process_project = _build_project(
        user_id="u1",
        name="Projeto Processo Novo",
        project_type=ProjectType.LAYOUT,
        responsible_login="Ana",
        planned_start=datetime(2026, 4, 1),
        planned_end=datetime(2026, 4, 30),
        process_classification=ProcessClassification.NEW,
    )
    existing_process_project = _build_project(
        user_id="u1",
        name="Projeto Processo Existente",
        project_type=ProjectType.LAYOUT,
        responsible_login="Ana",
        planned_start=datetime(2026, 4, 1),
        planned_end=datetime(2026, 4, 30),
        process_classification=ProcessClassification.EXISTING,
    )
    project_repo.save(new_process_project)
    project_repo.save(existing_process_project)

    new_task = new_process_project.start_new_task(
        "task-new",
        datetime(2026, 4, 1),
        datetime(2026, 4, 2),
    )
    new_task.add_manual_entry(
        datetime(2026, 4, 5, 8, 0),
        datetime(2026, 4, 7, 8, 0),
    )

    existing_task = existing_process_project.start_new_task(
        "task-existing",
        datetime(2026, 4, 1),
        datetime(2026, 4, 2),
    )
    existing_task.add_manual_entry(
        datetime(2026, 4, 8, 8, 0),
        datetime(2026, 4, 9, 8, 0),
    )

    routine_repo.save(
        RoutineActivity(
            user_id="u1",
            responsavel="Ana",
            tipo_atividade="Reuniões sobre Processos Novos",
            inicio=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
            horas_trabalhadas=12.0,
        )
    )
    routine_repo.save(
        RoutineActivity(
            user_id="u1",
            responsavel="Ana",
            tipo_atividade="Análise de Processos Novos",
            inicio=datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 4, 11, 20, 0, tzinfo=timezone.utc),
            horas_trabalhadas=12.0,
        )
    )
    routine_repo.save(
        RoutineActivity(
            user_id="u1",
            responsavel="Ana",
            tipo_atividade="Reuniões",
            inicio=datetime(2026, 4, 12, 8, 0, tzinfo=timezone.utc),
            fim=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            horas_trabalhadas=24.0,
        )
    )

    items = service.list_new_process_time_by_month()

    assert len(items) == 1
    assert items[0]["responsible_label"] == "Ana"
    assert items[0]["year"] == 2026
    assert items[0]["month"] == 4
    assert items[0]["month_label"] == "ABR"
    assert items[0]["period_label"] == "ABR 2026"
    assert isclose(items[0]["project_days"], 48.0 / 24.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(items[0]["routine_days"], 24.0 / 24.0, rel_tol=0, abs_tol=1e-10)
    assert isclose(items[0]["total_days"], 72.0 / 24.0, rel_tol=0, abs_tol=1e-10)
