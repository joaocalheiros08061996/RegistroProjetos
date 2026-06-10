from domain.repositories import IDashboardRepository


class DashboardService:
    _MONTH_LABELS = {
        1: "JAN",
        2: "FEV",
        3: "MAR",
        4: "ABR",
        5: "MAI",
        6: "JUN",
        7: "JUL",
        8: "AGO",
        9: "SET",
        10: "OUT",
        11: "NOV",
        12: "DEZ",
    }

    _PROJECT_TYPE_LABELS = {
        "LAYOUT": "LAYOUT",
        "EXPORTACAO": "EXPORTAÇÃO",
        "NORMATIZACAO": "NORMATIZAÇÃO",
        "PADRONIZACAO": "PADRONIZAÇÃO",
        "TRY_OUT": "TRY OUT",
        "MAPEAMENTO": "MAPEAMENTO",
        "MELHORIA": "MELHORIA DE PROC. EXISTENTES",
        "MELHORIA_PROC_NOVOS": "MELHORIA DE PROC. NOVOS",
        "PECAS": "PEÇAS",
    }

    def __init__(self, dashboard_repo: IDashboardRepository):
        self.dashboard_repo = dashboard_repo

    def list_avg_real_days_by_project_type(self) -> list[dict]:
        rows = self.dashboard_repo.list_avg_real_days_by_project_type()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            average_days = float(row.get("average_days") or 0.0)

            if not project_type or average_days <= 0:
                continue

            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "average_days": average_days,
                }
            )

        items.sort(key=lambda item: item["average_days"], reverse=True)
        return items

    def list_avg_planned_vs_real_days_by_project_type(self) -> list[dict]:
        rows = self.dashboard_repo.list_avg_planned_vs_real_days_by_project_type()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            planned_average_days = float(row.get("planned_average_days") or 0.0)
            real_average_days = float(row.get("real_average_days") or 0.0)

            if not project_type:
                continue

            if planned_average_days <= 0 and real_average_days <= 0:
                continue

            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "planned_average_days": planned_average_days,
                    "real_average_days": real_average_days,
                }
            )

        items.sort(
            key=lambda item: (
                item["real_average_days"],
                item["planned_average_days"],
            ),
            reverse=True,
        )
        return items

    def list_routine_total_days_by_month(self) -> list[dict]:
        rows = self.dashboard_repo.list_routine_total_days_by_month()

        items: list[dict] = []
        for row in rows:
            responsavel = str(
                row.get("responsavel") or row.get("user_label") or ""
            ).strip()
            activity_type = str(row.get("activity_type") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            total_days = float(row.get("total_days") or 0.0)

            if not responsavel:
                responsavel = "Sem responsável"

            if not activity_type or year <= 0 or month not in self._MONTH_LABELS:
                continue

            if total_days <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "user_id": responsavel,
                    "user_label": responsavel,
                    "responsavel": responsavel,
                    "activity_type": activity_type,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "total_days": total_days,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["activity_type"],
                item["responsavel"],
            )
            )
        return items

    def list_new_process_time_by_month(self) -> list[dict]:
        rows = self.dashboard_repo.list_new_process_time_by_month()

        items: list[dict] = []
        for row in rows:
            responsible_label = str(row.get("responsible_label") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            project_days = max(0.0, float(row.get("project_days") or 0.0))
            routine_days = max(0.0, float(row.get("routine_days") or 0.0))
            total_days = project_days + routine_days

            if not responsible_label:
                responsible_label = "Sem responsável"

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            if total_days <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "responsible_label": responsible_label,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "project_days": project_days,
                    "routine_days": routine_days,
                    "total_days": total_days,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["responsible_label"],
            )
        )
        return items

    @staticmethod
    def _format_user_label(user_id: str) -> str:
        if len(user_id) > 12:
            return f"Usuário {user_id[:4]}...{user_id[-4:]}"
        return user_id or "Sem usuário"

    def list_project_monthly_kpis(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_monthly_kpis()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)

            if not project_type or not responsible_login:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "project_count": max(0, int(row.get("project_count") or 0)),
                    "planned_days_sum": max(0.0, float(row.get("planned_days_sum") or 0.0)),
                    "planned_days_count": max(0, int(row.get("planned_days_count") or 0)),
                    "real_days_sum": max(0.0, float(row.get("real_days_sum") or 0.0)),
                    "real_days_count": max(0, int(row.get("real_days_count") or 0)),
                    "sla_breach_count": max(0, int(row.get("sla_breach_count") or 0)),
                    "sla_project_count": max(0, int(row.get("sla_project_count") or 0)),
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
            )
        )
        return items

    def list_project_complexity_counts(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_complexity_counts()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            complexity_score = int(row.get("complexity_score") or 0)
            project_count = int(row.get("project_count") or 0)

            if not project_type or complexity_score < 1 or complexity_score > 5:
                continue

            if project_count <= 0:
                continue

            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "complexity_score": complexity_score,
                    "project_count": project_count,
                }
            )

        items.sort(
            key=lambda item: (
                item["project_type_label"],
                item["complexity_score"],
            )
        )
        return items

    def list_project_complexity_counts_by_month(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_complexity_counts_by_month()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            complexity_score = int(row.get("complexity_score") or 0)
            project_count = int(row.get("project_count") or 0)

            if not project_type or not responsible_login:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            if complexity_score < 1 or complexity_score > 5:
                continue

            if project_count <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "complexity_score": complexity_score,
                    "project_count": project_count,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
                item["complexity_score"],
            )
        )
        return items

    def list_projects_by_responsible(self) -> list[dict]:
        rows = self.dashboard_repo.list_projects_by_responsible()

        items: list[dict] = []
        for row in rows:
            project_id = int(row.get("project_id") or 0)
            project_name = str(row.get("project_name") or "").strip()
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            planned_start = row.get("planned_start")
            planned_end = row.get("planned_end")
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)

            if project_id <= 0 or not project_name or not project_type:
                continue

            if not responsible_login:
                responsible_login = "Sem responsável"

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            task_count = max(0, int(row.get("task_count") or 0))
            completed_task_count = max(0, int(row.get("completed_task_count") or 0))
            percent_completed = max(0.0, min(100.0, float(row.get("percent_completed") or 0.0)))
            gut_score = max(1, int(row.get("gut_score") or 1))
            priority_level = int(row.get("priority_level") or 5)
            if priority_level < 1 or priority_level > 5:
                priority_level = 5
            complexity_score = int(row.get("complexity_score") or 1)
            if complexity_score < 1 or complexity_score > 5:
                complexity_score = 1

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "planned_start": planned_start,
                    "planned_end": planned_end,
                    "estimated_cost": max(0.0, float(row.get("estimated_cost") or 0.0)),
                    "task_count": task_count,
                    "completed_task_count": min(completed_task_count, task_count),
                    "percent_completed": round(percent_completed, 2),
                    "gut_score": gut_score,
                    "priority_level": priority_level,
                    "priority_label": str(
                        row.get("priority_label")
                        or f"Prioridade {priority_level}"
                    ),
                    "complexity_score": complexity_score,
                    "complexity_label": str(
                        row.get("complexity_label")
                        or f"Complexidade {complexity_score}"
                    ),
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                }
            )

        items.sort(
            key=lambda item: (
                item["responsible_login"],
                item["year"],
                item["month"],
                item["priority_level"],
                item["project_name"],
            )
        )
        return items

    def list_project_earned_value(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_earned_value()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            project_name = str(row.get("project_name") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)

            if not project_type or not responsible_login or not project_name:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            estimated_cost = max(0.0, float(row.get("estimated_cost") or 0.0))
            planned_value = max(0.0, float(row.get("planned_value") or 0.0))
            earned_value = max(0.0, float(row.get("earned_value") or 0.0))
            total_task_cost = max(0.0, float(row.get("total_task_cost") or 0.0))
            planned_effort_hours = max(0.0, float(row.get("planned_effort_hours") or 0.0))
            actual_effort_hours = max(0.0, float(row.get("actual_effort_hours") or 0.0))
            planned_labor_cost = max(0.0, float(row.get("planned_labor_cost") or 0.0))
            actual_labor_cost = max(0.0, float(row.get("actual_labor_cost") or 0.0))
            actual_cost = max(0.0, float(row.get("actual_cost") or 0.0))

            if (
                estimated_cost <= 0
                and total_task_cost <= 0
                and planned_value <= 0
                and earned_value <= 0
                and planned_labor_cost <= 0
                and actual_cost <= 0
            ):
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_id": int(row.get("project_id") or 0),
                    "project_name": project_name,
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "estimated_cost": estimated_cost,
                    "planned_value": planned_value,
                    "earned_value": earned_value,
                    "total_task_cost": total_task_cost,
                    "planned_effort_hours": planned_effort_hours,
                    "actual_effort_hours": actual_effort_hours,
                    "planned_labor_cost": planned_labor_cost,
                    "actual_labor_cost": actual_labor_cost,
                    "actual_cost": actual_cost,
                    "task_count": max(0, int(row.get("task_count") or 0)),
                    "completed_task_count": max(0, int(row.get("completed_task_count") or 0)),
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
                item["project_name"],
            )
        )
        return items

    def list_project_effort_deviation(self) -> list[dict]:
        rows = self.dashboard_repo.list_project_effort_deviation()

        items: list[dict] = []
        for row in rows:
            project_type = str(row.get("project_type") or "").strip().upper()
            responsible_login = str(row.get("responsible_login") or "").strip()
            year = int(row.get("year") or 0)
            month = int(row.get("month") or 0)
            task_count = max(0, int(row.get("task_count") or 0))
            planned_effort_hours = max(0.0, float(row.get("planned_effort_hours") or 0.0))
            actual_effort_hours = max(0.0, float(row.get("actual_effort_hours") or 0.0))
            planned_labor_cost = max(0.0, float(row.get("planned_labor_cost") or 0.0))
            actual_labor_cost = max(0.0, float(row.get("actual_labor_cost") or 0.0))

            if not project_type or not responsible_login:
                continue

            if year <= 0 or month not in self._MONTH_LABELS:
                continue

            if task_count <= 0 or planned_effort_hours <= 0 or actual_effort_hours <= 0:
                continue

            month_label = self._MONTH_LABELS[month]
            items.append(
                {
                    "project_type": project_type,
                    "project_type_label": self._PROJECT_TYPE_LABELS.get(
                        project_type,
                        project_type.replace("_", " "),
                    ),
                    "responsible_login": responsible_login,
                    "year": year,
                    "month": month,
                    "month_label": month_label,
                    "period_label": f"{month_label} {year}",
                    "task_count": task_count,
                    "planned_effort_hours": planned_effort_hours,
                    "actual_effort_hours": actual_effort_hours,
                    "effort_deviation_hours": actual_effort_hours - planned_effort_hours,
                    "planned_labor_cost": planned_labor_cost,
                    "actual_labor_cost": actual_labor_cost,
                    "labor_cost_deviation": actual_labor_cost - planned_labor_cost,
                }
            )

        items.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["project_type_label"],
                item["responsible_login"],
            )
        )
        return items
