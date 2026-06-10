import unicodedata

from domain.project import Project
from domain.task import Task
from domain.time_entry import TimeEntry
from domain.enums import (
    MethodClarity,
    ObjectiveClarity,
    ProcessClassification,
    ProjectType,
    Severity,
    TaskStatus,
    Trend,
    Urgency,
)
from domain.repositories import IProjectRepository
from infra.database.connection import get_connection
from psycopg2.extras import RealDictCursor


def _normalize_enum_token(raw_value) -> str:
    normalized = unicodedata.normalize("NFKD", str(raw_value).strip())
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    normalized = normalized.casefold().replace("-", " ").replace("_", " ")
    return " ".join(normalized.split())


class SupabaseProjectRepository(IProjectRepository):
    _COMPLETED_STATUS_SQL = (
        "replace(replace(upper(trim(status)), '-', '_'), ' ', '_') "
        "in ('COMPLETED', 'COMPLETE')"
    )

    @staticmethod
    def _coerce_enum(enum_cls, raw_value):
        """
        Aceita valor textual do enum (novo formato) ou nome do membro (legado).
        """
        if isinstance(raw_value, enum_cls):
            return raw_value
        if raw_value is None:
            raise ValueError(f"Valor ausente para enum {enum_cls.__name__}")

        value = str(raw_value).strip()

        try:
            return enum_cls(value)
        except ValueError:
            pass

        if value in enum_cls.__members__:
            return enum_cls[value]

        normalized = _normalize_enum_token(value)
        for member in enum_cls:
            if normalized in {
                _normalize_enum_token(member.value),
                _normalize_enum_token(member.name),
            }:
                return member

        raise ValueError(
            f"Valor invalido para enum {enum_cls.__name__}: {raw_value!r}"
        )

    @staticmethod
    def _coerce_task_status(raw_value) -> TaskStatus:
        """
        Aceita formatos novos e legados de status.
        Exemplos legados: "Completed", "In Progress", "Paused", "Planned".
        """
        if isinstance(raw_value, TaskStatus):
            return raw_value
        if raw_value is None:
            raise ValueError("Valor ausente para TaskStatus")

        value = str(raw_value).strip()

        try:
            return TaskStatus(value)
        except ValueError:
            pass

        normalized = value.upper().replace("-", "_").replace(" ", "_")
        normalized = {
            "INPROGRESS": "IN_PROGRESS",
            "COMPLETE": "COMPLETED",
        }.get(normalized, normalized)

        if normalized in TaskStatus.__members__:
            return TaskStatus[normalized]

        raise ValueError(f"Status de tarefa invalido: {raw_value!r}")

    # ============================================================
    # SAVE
    # ============================================================

    def save(self, project: Project) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            if project.id is None:
                cur.execute(
                    """
                    insert into projects (
                        user_id,
                        name,
                        description,
                        project_type,
                        process_classification,
                        responsible_login,
                        fte,
                        planned_start,
                        planned_end,
                        severity,
                        urgency,
                        trend,
                        objective,
                        method,
                        estimated_cost
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    returning id
                    """,
                    (
                        project.user_id,
                        project.name,
                        project.description,
                        project.project_type.value,
                        (
                            project.process_classification.value
                            if project.process_classification
                            else None
                        ),
                        project.responsible_login,
                        project.fte,
                        project.planned_start,
                        project.planned_end,
                        project.severity.value,
                        project.urgency.value,
                        project.trend.value,
                        project.objective_clarity.value,
                        project.method_clarity.value,
                        project.estimated_cost,
                    ),
                )
                project._set_id(cur.fetchone()[0])

            conn.commit()

        return project.id

    # ============================================================
    # FIND
    # ============================================================

    def find_by_id(self, project_id: int, user_id: str):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    select *
                    from projects
                    where id = %s and user_id = %s
                    """,
                    (project_id, user_id),
                )
                row = cur.fetchone()

            if not row:
                return None

            project = self._build_project(row)
            self._load_tasks(conn, project)

            return project

    # ============================================================
    # LIST
    # ============================================================

    def list_by_user(self, user_id: str):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    select *
                    from projects
                    where user_id = %s
                    order by created_at
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()

            projects = []

            for row in rows:
                project = self._build_project(row)
                self._load_tasks(conn, project)
                projects.append(project)

            return projects

    def list_summary_by_user(self, user_id: str) -> list[dict]:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    with scoped_tasks as (
                        select
                            project_id,
                            {self._COMPLETED_STATUS_SQL} as is_completed
                        from tasks
                        where user_id = %s
                    ),
                    task_counts as (
                        select
                            project_id,
                            count(*)::int as task_count,
                            count(*) filter (where is_completed)::int
                                as completed_task_count
                        from scoped_tasks
                        group by project_id
                    )
                    select
                        p.*,
                        coalesce(tc.task_count, 0)::int as task_count,
                        coalesce(tc.completed_task_count, 0)::int
                            as completed_task_count
                    from projects p
                    left join task_counts tc on tc.project_id = p.id
                    where p.user_id = %s
                    order by p.created_at
                    """,
                    (user_id, user_id),
                )
                rows = cur.fetchall()

        return [self._build_project_summary(row) for row in rows]

    def find_detail_summary(self, project_id: int, user_id: str):
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    with scoped_tasks as (
                        select
                            id,
                            name,
                            {self._COMPLETED_STATUS_SQL} as is_completed
                        from tasks
                        where project_id = %s and user_id = %s
                    )
                    select
                        p.*,
                        (select count(*)::int from scoped_tasks) as task_count,
                        (
                            select count(*)::int
                            from scoped_tasks
                            where is_completed
                        ) as completed_task_count,
                        coalesce(
                            (
                                select array_agg(name order by id)
                                from scoped_tasks
                                where not is_completed
                            ),
                            array[]::text[]
                        ) as active_tasks,
                        coalesce(
                            (
                                select sum(
                                    greatest(
                                        extract(
                                            epoch from (
                                                coalesce(te.end_time, now())
                                                - te.start_time
                                            )
                                        ),
                                        0.0
                                    )
                                )
                                from scoped_tasks st
                                join time_entries te on te.task_id = st.id
                            ),
                            0.0
                        ) as actual_seconds
                    from projects p
                    where p.id = %s and p.user_id = %s
                    """,
                    (project_id, user_id, project_id, user_id),
                )
                row = cur.fetchone()

        if not row:
            return None
        return self._build_project_detail_summary(row)

    # ============================================================
    # DELETE
    # ============================================================

    def delete(self, project_id: int, user_id: str) -> bool:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                delete from projects
                where id = %s and user_id = %s
                """,
                (project_id, user_id),
            )
            deleted = cur.rowcount > 0
            conn.commit()

        return deleted

    # ============================================================
    # BUILD PROJECT (HYDRATION)
    # ============================================================

    def _build_project(self, row: dict) -> Project:
        objective_raw = row.get("objective_clarity", row.get("objective"))
        method_raw = row.get("method_clarity", row.get("method"))
        process_classification_raw = row.get("process_classification")
        process_classification = None
        if process_classification_raw and str(process_classification_raw).strip():
            process_classification = self._coerce_enum(
                ProcessClassification,
                process_classification_raw,
            )

        project = Project(
            user_id=row["user_id"],
            name=row["name"],
            description=row.get("description") or "",
            project_type=self._coerce_enum(ProjectType, row["project_type"]),
            process_classification=process_classification,
            responsible_login=row["responsible_login"],
            fte=row["fte"],
            planned_start=row["planned_start"],
            planned_end=row["planned_end"],
            severity=self._coerce_enum(Severity, row["severity"]),
            urgency=self._coerce_enum(Urgency, row["urgency"]),
            trend=self._coerce_enum(Trend, row["trend"]),
            objective_clarity=self._coerce_enum(
                ObjectiveClarity,
                objective_raw,
            ),
            method_clarity=self._coerce_enum(
                MethodClarity,
                method_raw,
            ),
            estimated_cost=row["estimated_cost"],
        )

        project._set_id(row["id"])
        return project

    def _build_project_summary(self, row: dict) -> dict:
        project = self._build_project(row)
        task_count = max(0, int(row.get("task_count") or 0))
        completed_task_count = max(0, int(row.get("completed_task_count") or 0))
        completed_task_count = min(completed_task_count, task_count)
        percent_completed = (
            round((completed_task_count / task_count) * 100.0, 2)
            if task_count
            else 0.0
        )

        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "project_type": project.project_type.value,
            "process_classification": (
                project.process_classification.value
                if project.process_classification
                else None
            ),
            "responsible_login": project.responsible_login,
            "planned_start": project.planned_start,
            "planned_end": project.planned_end,
            "estimated_cost": project.estimated_cost,
            "task_count": task_count,
            "percent_completed": percent_completed,
            "gut_score": project.gut_score,
            "priority_level": project.priority_level,
            "priority_label": project.priority_label,
            "complexity_score": project.complexity_score,
            "complexity_label": project.complexity_label,
        }

    def _build_project_detail_summary(self, row: dict) -> dict:
        project = self._build_project(row)
        summary = self._build_project_summary(row)
        actual_seconds = max(0.0, float(row.get("actual_seconds") or 0.0))
        active_tasks = list(row.get("active_tasks") or [])

        summary.update(
            {
                "fte": project.fte,
                "severity": project.severity.value,
                "urgency": project.urgency.value,
                "trend": project.trend.value,
                "objective_clarity": project.objective_clarity.value,
                "method_clarity": project.method_clarity.value,
                "actual_days": actual_seconds / 86400.0,
                "active_tasks": active_tasks,
            }
        )
        return summary

    # ============================================================
    # LOAD TASKS
    # ============================================================

    def _load_tasks(self, conn, project: Project) -> None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select *
                from tasks
                where project_id = %s and user_id = %s
                order by id
                """,
                (project.id, project.user_id),
            )
            tasks = cur.fetchall()

        for row in tasks:
            task = Task(
                name=row["name"],
                planned_start=row["planned_start"],
                planned_end=row["planned_end"],
                cost=row["cost"],
                description=row.get("description") or "",
            )

            task._set_id(row["id"])
            task._set_status(self._coerce_task_status(row["status"]))

            self._load_time_entries(conn, task)
            project.add_task(task)

    # ============================================================
    # LOAD TIME ENTRIES
    # ============================================================

    def _load_time_entries(self, conn, task: Task) -> None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select start_time, end_time
                from time_entries
                where task_id = %s
                order by start_time
                """,
                (task.id,),
            )
            rows = cur.fetchall()

        for row in rows:
            entry = TimeEntry(start=row["start_time"])

            if row["end_time"] is not None:
                entry.stop(row["end_time"])

            task._add_time_entry(entry)
