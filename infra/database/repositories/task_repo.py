from datetime import datetime
from typing import Optional

from domain.task import Task
from domain.time_entry import TimeEntry
from domain.enums import TaskStatus
from domain.repositories import ITaskRepository
from infra.database.connection import get_connection
from psycopg2.extras import RealDictCursor


class SupabaseTaskRepository(ITaskRepository):
    _COMPLETED_STATUS_SQL = (
        "replace(replace(upper(trim(t.status)), '-', '_'), ' ', '_') "
        "in ('COMPLETED', 'COMPLETE')"
    )

    @staticmethod
    def _coerce_task_status(raw_value) -> TaskStatus:
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

    def save(self, task: Task, project_id: int, user_id: str) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            if task.id is None:
                cur.execute(
                    """
                    insert into tasks (
                        project_id, user_id, name,
                        planned_start, planned_end, cost, status, description
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s)
                    returning id
                    """,
                    (
                        project_id,
                        user_id,
                        task.name,
                        task.planned_start,
                        task.planned_end,
                        task.cost,
                        task.status.value,
                        task.description,
                    ),
                )
                task._set_id(cur.fetchone()[0])
            conn.commit()
        return task.id

    def find_by_id(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
    ) -> Optional[Task]:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    select *
                    from tasks
                    where id = %s and project_id = %s and user_id = %s
                    """,
                    (task_id, project_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None

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
            return task

    def find_by_name(
        self,
        project_id: int,
        user_id: str,
        task_name: str,
    ) -> Optional[Task]:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    select *
                    from tasks
                    where project_id = %s and user_id = %s and name = %s
                    """,
                    (project_id, user_id, task_name),
                )
                row = cur.fetchone()
                if not row:
                    return None

            task = self._build_task(row)
            self._load_time_entries(conn, task)
            return task

    def find_id_by_name(
        self,
        project_id: int,
        user_id: str,
        task_name: str,
    ) -> Optional[int]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id
                    from tasks
                    where project_id = %s and user_id = %s and name = %s
                    """,
                    (project_id, user_id, task_name),
                )
                row = cur.fetchone()
        return int(row[0]) if row else None

    def find_summary_by_name(
        self,
        project_id: int,
        user_id: str,
        task_name: str,
    ) -> Optional[dict]:
        rows = self._fetch_task_summaries(
            project_id=project_id,
            user_id=user_id,
            task_name=task_name,
            include_completed=True,
        )
        return rows[0] if rows else None

    def list_with_time_summary(
        self,
        project_id: int,
        user_id: str,
        include_completed: bool = True,
    ) -> list[dict]:
        return self._fetch_task_summaries(
            project_id=project_id,
            user_id=user_id,
            include_completed=include_completed,
        )

    def delete_by_name(self, project_id: int, user_id: str, task_name: str) -> bool:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                delete from tasks
                where project_id = %s and user_id = %s and name = %s
                """,
                (project_id, user_id, task_name),
            )
            deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    def delete_by_project(self, project_id: int, user_id: str) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                delete from tasks
                where project_id = %s and user_id = %s
                """,
                (project_id, user_id),
            )
            deleted_count = cur.rowcount
            conn.commit()
        return deleted_count

    def _fetch_task_summaries(
        self,
        *,
        project_id: int,
        user_id: str,
        task_name: str | None = None,
        include_completed: bool = True,
    ) -> list[dict]:
        filters = ["t.project_id = %s", "t.user_id = %s"]
        params: list[object] = [project_id, user_id]

        if task_name is not None:
            filters.append("t.name = %s")
            params.append(task_name)

        if not include_completed:
            filters.append(f"not ({self._COMPLETED_STATUS_SQL})")

        where_clause = " and ".join(filters)

        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    with scoped_tasks as (
                        select t.*
                        from tasks t
                        where {where_clause}
                    ),
                    time_summary as (
                        select
                            te.task_id,
                            count(*)::int as time_entries_count,
                            sum(
                                greatest(
                                    extract(
                                        epoch from (
                                            coalesce(te.end_time, now())
                                            - te.start_time
                                        )
                                    ),
                                    0.0
                                )
                            ) as actual_seconds
                        from time_entries te
                        join scoped_tasks st on st.id = te.task_id
                        group by te.task_id
                    )
                    select
                        t.id,
                        t.name,
                        t.status,
                        t.planned_start,
                        t.planned_end,
                        t.cost,
                        t.description,
                        coalesce(te.actual_seconds, 0.0) as actual_seconds,
                        coalesce(te.time_entries_count, 0)::int
                            as time_entries_count
                    from scoped_tasks t
                    left join time_summary te on te.task_id = t.id
                    order by t.id
                    """,
                    tuple(params),
                )
                rows = cur.fetchall()

        return [self._build_task_summary(row) for row in rows]

    def _build_task(self, row: dict) -> Task:
        task = Task(
            name=row["name"],
            planned_start=row["planned_start"],
            planned_end=row["planned_end"],
            cost=row["cost"],
            description=row.get("description") or "",
        )
        task._set_id(row["id"])
        task._set_status(self._coerce_task_status(row["status"]))
        return task

    def _build_task_summary(self, row: dict) -> dict:
        status = self._coerce_task_status(row["status"])
        actual_seconds = max(0.0, float(row.get("actual_seconds") or 0.0))
        return {
            "name": row["name"],
            "status": status.value,
            "planned_start": row["planned_start"],
            "planned_end": row["planned_end"],
            "cost": row["cost"],
            "description": row.get("description") or "",
            "actual_seconds": round(actual_seconds, 2),
            "time_entries_count": int(row.get("time_entries_count") or 0),
            "percent_completed": 100.0 if status == TaskStatus.COMPLETED else 0.0,
        }

    def append_time_entry(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
        entry: TimeEntry,
    ) -> None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "insert into time_entries (task_id, start_time, end_time) values (%s,%s,%s)",
                (task_id, entry.start, entry.end),
            )
            conn.commit()

    def update_status(self, task_id: int, status: str) -> None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "update tasks set status = %s where id = %s",
                (status, task_id),
            )
            conn.commit()

    def start_time_entry(self, task_id: int, start: datetime) -> None:
        self.append_time_entry(task_id, None, None, TimeEntry(start))

    def close_open_time_entry(self, task_id: int, end: datetime) -> None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update time_entries
                set end_time = %s
                where id = (
                    select id
                    from time_entries
                    where task_id = %s and end_time is null
                    order by start_time desc
                    limit 1
                )
                """,
                (end, task_id),
            )
            conn.commit()

    def _load_time_entries(self, conn, task: Task) -> None:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "select start_time, end_time from time_entries where task_id = %s",
                (task.id,),
            )
            rows = cur.fetchall()

        for row in rows:
            entry = TimeEntry(start=row["start_time"])
            if row["end_time"]:
                entry.stop(row["end_time"])
            task._add_time_entry(entry)

    def list_time_entries(self, task_id: int) -> list[tuple]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select start_time, end_time
                    from time_entries
                    where task_id = %s
                    order by start_time
                    """,
                    (task_id,),
                )
                rows = cur.fetchall()
        return [(row[0], row[1]) for row in rows]
