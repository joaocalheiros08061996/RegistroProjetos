from domain.entities import Project, Task, TimeEntry
from domain.enums import (
    MethodClarity,
    ObjectiveClarity,
    ProjectType,
    Severity,
    TaskStatus,
    Trend,
    Urgency,
)
from domain.repositories import IProjectRepository
from infra.database.connection import get_connection
from psycopg2.extras import RealDictCursor


class SupabaseProjectRepository(IProjectRepository):
    @staticmethod
    def _coerce_enum(enum_cls, raw_value):
        """
        Aceita valor textual do enum (novo formato) ou nome do membro (legado).
        """
        if isinstance(raw_value, enum_cls):
            return raw_value
        if raw_value is None:
            raise ValueError(f"Valor ausente para enum {enum_cls.__name__}")

        try:
            return enum_cls(raw_value)
        except ValueError:
            return enum_cls[str(raw_value)]

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
                        project_type,
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
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    returning id
                    """,
                    (
                        project.user_id,
                        project.name,
                        project.project_type.value,
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

    # ============================================================
    # BUILD PROJECT (HYDRATION)
    # ============================================================

    def _build_project(self, row: dict) -> Project:
        objective_raw = row.get("objective_clarity", row.get("objective"))
        method_raw = row.get("method_clarity", row.get("method"))

        project = Project(
            user_id=row["user_id"],
            name=row["name"],
            project_type=self._coerce_enum(ProjectType, row["project_type"]),
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
