from domain.constants import ENGINEERING_PROCESS_HOURLY_RATE, WORKDAY_HOURS, WORKDAY_SECONDS
from domain.repositories import IDashboardRepository
from infra.database.connection import get_connection
from psycopg2.extras import RealDictCursor


def _weekday_calendar_days_sql(start_expr: str, end_expr: str) -> str:
    return f"""
        (
            select coalesce(sum(
                greatest(
                    0,
                    extract(epoch from (
                        least({end_expr}, workday + interval '1 day')
                        - greatest({start_expr}, workday)
                    ))
                ) / 86400.0
            ), 0)
            from generate_series(
                date_trunc('day', {start_expr}),
                date_trunc('day', {end_expr}),
                interval '1 day'
            ) as workdays(workday)
            where workday < {end_expr}
              and extract(isodow from workday) between 1 and 5
        )
    """


def _planned_workdays_sql(start_expr: str, end_expr: str) -> str:
    weekday_days = _weekday_calendar_days_sql(start_expr, end_expr)
    return f"""
        case
            when {start_expr} is null
              or {end_expr} is null
              or {end_expr} <= {start_expr}
                then 0
            when {start_expr}::date = {end_expr}::date
                then extract(epoch from ({end_expr} - {start_expr})) / {WORKDAY_SECONDS}.0
            else {weekday_days}
        end
    """


def _planned_hours_sql(start_expr: str, end_expr: str) -> str:
    weekday_days = _weekday_calendar_days_sql(start_expr, end_expr)
    return f"""
        case
            when {start_expr} is null
              or {end_expr} is null
              or {end_expr} <= {start_expr}
                then 0
            when {start_expr}::date = {end_expr}::date
                then extract(epoch from ({end_expr} - {start_expr})) / 3600.0
            else ({weekday_days}) * {WORKDAY_HOURS}
        end
    """


def _planned_progress_sql(start_expr: str, end_expr: str) -> str:
    elapsed_days = _weekday_calendar_days_sql(start_expr, "now()")
    planned_days = _weekday_calendar_days_sql(start_expr, end_expr)
    return f"""
        case
            when {start_expr} is null
              or {end_expr} is null
              or {end_expr} <= {start_expr}
                then null
            when now() <= {start_expr}
                then 0
            when now() >= {end_expr}
                then 1
            when {start_expr}::date = {end_expr}::date
                then extract(epoch from (now() - {start_expr}))
                     / nullif(extract(epoch from ({end_expr} - {start_expr})), 0)
            else ({elapsed_days}) / nullif(({planned_days}), 0)
        end
    """


class SupabaseDashboardRepository(IDashboardRepository):
    def list_avg_real_days_by_project_type(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                with project_real_days as (
                    select
                        p.id as project_id,
                        p.project_type as project_type,
                        sum(extract(epoch from (te.end_time - te.start_time))) / 86400.0 as real_days
                    from projects p
                    join tasks t on t.project_id = p.id
                    join time_entries te on te.task_id = t.id
                    where te.end_time is not null
                    group by p.id, p.project_type
                )
                select
                    project_type,
                    avg(real_days) as average_days
                from project_real_days
                where real_days > 0
                group by project_type
                order by average_days desc, project_type asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_type": row["project_type"],
                "average_days": float(row["average_days"] or 0.0),
            }
            for row in rows
        ]

    def list_avg_planned_vs_real_days_by_project_type(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                with planned_type as (
                    select
                        p.project_type as project_type,
                        avg(extract(epoch from (p.planned_end - p.planned_start)) / 86400.0) as planned_average_days
                    from projects p
                    group by p.project_type
                ),
                real_project as (
                    select
                        p.id as project_id,
                        p.project_type as project_type,
                        sum(extract(epoch from (te.end_time - te.start_time)) / 86400.0) as real_days
                    from projects p
                    join tasks t on t.project_id = p.id
                    join time_entries te on te.task_id = t.id
                    where te.end_time is not null
                    group by p.id, p.project_type
                ),
                real_type as (
                    select
                        project_type,
                        avg(real_days) as real_average_days
                    from real_project
                    where real_days > 0
                    group by project_type
                )
                select
                    coalesce(pl.project_type, rt.project_type) as project_type,
                    pl.planned_average_days as planned_average_days,
                    rt.real_average_days as real_average_days
                from planned_type pl
                full join real_type rt
                    on rt.project_type = pl.project_type
                where coalesce(pl.planned_average_days, 0) > 0
                   or coalesce(rt.real_average_days, 0) > 0
                order by
                    coalesce(rt.real_average_days, 0) desc,
                    coalesce(pl.planned_average_days, 0) desc,
                    coalesce(pl.project_type, rt.project_type) asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_type": row["project_type"],
                "planned_average_days": float(row["planned_average_days"] or 0.0),
                "real_average_days": float(row["real_average_days"] or 0.0),
            }
            for row in rows
        ]

    def list_routine_total_days_by_month(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'atividades'
                """
            )
            columns = {row["column_name"] for row in (cur.fetchall() or [])}

            if "tipo_atividade" not in columns:
                return []

            responsible_expr = (
                "coalesce(nullif(trim(responsavel::text), ''), 'Sem responsável')"
                if "responsavel" in columns
                else "'Sem responsável'"
            )

            def year_value_expr(column_name: str) -> str:
                return f"""
                    case
                        when trim({column_name}::text) ~ '^[0-9]+(\\.[0-9]+)?$'
                            then floor({column_name}::numeric)::int
                    end
                """

            def month_value_expr(column_name: str) -> str:
                return f"""
                    case
                        when trim({column_name}::text) ~ '^[0-9]+(\\.[0-9]+)?$'
                            then floor({column_name}::numeric)::int
                        when upper(left(trim({column_name}::text), 3)) = 'JAN' then 1
                        when upper(left(trim({column_name}::text), 3)) = 'FEV' then 2
                        when upper(left(trim({column_name}::text), 3)) = 'MAR' then 3
                        when upper(left(trim({column_name}::text), 3)) = 'ABR' then 4
                        when upper(left(trim({column_name}::text), 3)) = 'MAI' then 5
                        when upper(left(trim({column_name}::text), 3)) = 'JUN' then 6
                        when upper(left(trim({column_name}::text), 3)) = 'JUL' then 7
                        when upper(left(trim({column_name}::text), 3)) = 'AGO' then 8
                        when upper(left(trim({column_name}::text), 3)) = 'SET' then 9
                        when upper(left(trim({column_name}::text), 3)) = 'OUT' then 10
                        when upper(left(trim({column_name}::text), 3)) = 'NOV' then 11
                        when upper(left(trim({column_name}::text), 3)) = 'DEZ' then 12
                    end
                """

            year_parts: list[str] = []
            month_parts: list[str] = []
            worked_hour_rules: list[str] = []

            if "ano" in columns:
                year_parts.append(year_value_expr("ano"))
            if "inicio" in columns:
                year_parts.append("extract(year from inicio)::int")

            if "mes" in columns:
                month_parts.append(month_value_expr("mes"))
            if "mes_nome" in columns:
                month_parts.append(month_value_expr("mes_nome"))
            if "inicio" in columns:
                month_parts.append("extract(month from inicio)::int")

            if "horas_trabalhadas" in columns:
                worked_hour_rules.append(
                    """
                    when horas_trabalhadas is not null
                         and replace(trim(horas_trabalhadas::text), ',', '.') ~ '^[0-9]+(\\.[0-9]+)?$'
                         and replace(trim(horas_trabalhadas::text), ',', '.')::numeric > 0
                        then replace(trim(horas_trabalhadas::text), ',', '.')::numeric
                    """
                )
            if "inicio" in columns and "fim" in columns:
                worked_hour_rules.append(
                    """
                    when fim is not null and inicio is not null and fim > inicio
                        then extract(epoch from (fim - inicio)) / 3600.0
                    """
                )

            if not year_parts or not month_parts or not worked_hour_rules:
                return []

            year_expr = (
                year_parts[0]
                if len(year_parts) == 1
                else f"coalesce({', '.join(year_parts)})"
            )
            month_expr = (
                month_parts[0]
                if len(month_parts) == 1
                else f"coalesce({', '.join(month_parts)})"
            )
            worked_hours_expr = "case " + " ".join(worked_hour_rules) + " else 0 end"

            cur.execute(
                f"""
                with routine_hours as (
                    select
                        {responsible_expr} as responsavel,
                        tipo_atividade as activity_type,
                        {year_expr} as year,
                        {month_expr} as month,
                        {worked_hours_expr} as worked_hours
                    from atividades
                    where tipo_atividade is not null
                )
                select
                    responsavel,
                    activity_type,
                    year,
                    month,
                    sum(worked_hours) / {WORKDAY_HOURS} as total_days
                from routine_hours
                where year is not null
                  and month between 1 and 12
                group by responsavel, activity_type, year, month
                having sum(worked_hours) > 0
                order by year asc, month asc, activity_type asc, responsavel asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "user_id": row["responsavel"],
                "user_label": row["responsavel"],
                "responsavel": row["responsavel"],
                "activity_type": row["activity_type"],
                "year": int(row["year"]),
                "month": int(row["month"]),
                "total_days": float(row["total_days"] or 0.0),
            }
            for row in rows
        ]

    def list_project_monthly_kpis(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                with project_real_days as (
                    select
                        p.id as project_id,
                        sum(extract(epoch from (te.end_time - te.start_time))) / 86400.0 as real_days
                    from projects p
                    join tasks t on t.project_id = p.id
                    join time_entries te on te.task_id = t.id
                    where te.end_time is not null
                    group by p.id
                ),
                project_base as (
                    select
                        p.id as project_id,
                        p.project_type,
                        p.responsible_login,
                        extract(year from p.planned_start)::int as year,
                        extract(month from p.planned_start)::int as month,
                        extract(epoch from (p.planned_end - p.planned_start)) / 86400.0 as planned_days,
                        coalesce(pr.real_days, 0) as real_days
                    from projects p
                    left join project_real_days pr on pr.project_id = p.id
                    where p.planned_start is not null
                )
                select
                    project_type,
                    responsible_login,
                    year,
                    month,
                    count(*)::int as project_count,
                    coalesce(sum(
                        case
                            when real_days > 0 and planned_days > 0 then planned_days
                            else 0
                        end
                    ), 0) as planned_days_sum,
                    count(
                        case
                            when real_days > 0 and planned_days > 0 then 1
                        end
                    )::int as planned_days_count,
                    coalesce(sum(
                        case
                            when real_days > 0 then real_days
                            else 0
                        end
                    ), 0) as real_days_sum,
                    count(
                        case
                            when real_days > 0 then 1
                        end
                    )::int as real_days_count,
                    coalesce(sum(
                        case
                            when real_days > 0
                             and planned_days > 0
                             and real_days > planned_days
                                then 1
                            else 0
                        end
                    ), 0)::int as sla_breach_count,
                    count(
                        case
                            when real_days > 0 and planned_days > 0 then 1
                        end
                    )::int as sla_project_count
                from project_base
                group by project_type, responsible_login, year, month
                order by year asc, month asc, project_type asc, responsible_login asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_type": row["project_type"],
                "responsible_login": row["responsible_login"],
                "year": int(row["year"]),
                "month": int(row["month"]),
                "project_count": int(row["project_count"] or 0),
                "planned_days_sum": float(row["planned_days_sum"] or 0.0),
                "planned_days_count": int(row["planned_days_count"] or 0),
                "real_days_sum": float(row["real_days_sum"] or 0.0),
                "real_days_count": int(row["real_days_count"] or 0),
                "sla_breach_count": int(row["sla_breach_count"] or 0),
                "sla_project_count": int(row["sla_project_count"] or 0),
            }
            for row in rows
        ]

    def list_project_complexity_counts(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                with classified_projects as (
                    select
                        p.project_type,
                        case
                            when trim(p.objective::text) in ('Objetivo totalmente definido', 'FULLY_DEFINED')
                                then 1
                            when trim(p.objective::text) in ('Objetivo claro com pequenas ambiguidades', 'CLEAR_WITH_AMBIGUITIES')
                                then 2
                            when trim(p.objective::text) in ('Objetivo parcialmente definido', 'PARTIALLY_DEFINED')
                                then 3
                            when trim(p.objective::text) in ('Objetivo pouco claro', 'UNCLEAR')
                                then 4
                            when trim(p.objective::text) in ('Objetivo indefinido ou exploratório', 'UNDEFINED')
                                then 5
                        end as objective_score,
                        case
                            when trim(p.method::text) in ('Métodos totalmente definidos e dominados', 'FULLY_DEFINED')
                                then 1
                            when trim(p.method::text) in (
                                'Métodos conhecidos com pequenas adaptações',
                                'Métodos definidos com pequenas alterações',
                                'KNOWN_WITH_ADAPTATIONS'
                            )
                                then 2
                            when trim(p.method::text) in ('Métodos parcialmente conhecidos', 'PARTIALLY_KNOWN')
                                then 3
                            when trim(p.method::text) in ('Métodos pouco definidos', 'POORLY_DEFINED')
                                then 4
                            when trim(p.method::text) in ('Métodos desconhecidos ou inexistentes', 'UNKNOWN')
                                then 5
                        end as method_score
                    from projects p
                    where p.project_type is not null
                ),
                project_complexity as (
                    select
                        project_type,
                        least(
                            5,
                            greatest(
                                1,
                                ceil((objective_score * method_score)::numeric / 5.0)::int
                            )
                        ) as complexity_score
                    from classified_projects
                    where objective_score is not null
                      and method_score is not null
                )
                select
                    project_type,
                    complexity_score,
                    count(*)::int as project_count
                from project_complexity
                group by project_type, complexity_score
                order by project_type asc, complexity_score asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_type": row["project_type"],
                "complexity_score": int(row["complexity_score"] or 0),
                "project_count": int(row["project_count"] or 0),
            }
            for row in rows
        ]

    def list_project_complexity_counts_by_month(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                with classified_projects as (
                    select
                        p.project_type,
                        coalesce(nullif(trim(p.responsible_login::text), ''), 'Sem responsável') as responsible_login,
                        extract(year from p.planned_start)::int as year,
                        extract(month from p.planned_start)::int as month,
                        case
                            when trim(p.objective::text) in ('Objetivo totalmente definido', 'FULLY_DEFINED')
                                then 1
                            when trim(p.objective::text) in ('Objetivo claro com pequenas ambiguidades', 'CLEAR_WITH_AMBIGUITIES')
                                then 2
                            when trim(p.objective::text) in ('Objetivo parcialmente definido', 'PARTIALLY_DEFINED')
                                then 3
                            when trim(p.objective::text) in ('Objetivo pouco claro', 'UNCLEAR')
                                then 4
                            when trim(p.objective::text) in ('Objetivo indefinido ou exploratório', 'UNDEFINED')
                                then 5
                        end as objective_score,
                        case
                            when trim(p.method::text) in ('Métodos totalmente definidos e dominados', 'FULLY_DEFINED')
                                then 1
                            when trim(p.method::text) in (
                                'Métodos conhecidos com pequenas adaptações',
                                'Métodos definidos com pequenas alterações',
                                'KNOWN_WITH_ADAPTATIONS'
                            )
                                then 2
                            when trim(p.method::text) in ('Métodos parcialmente conhecidos', 'PARTIALLY_KNOWN')
                                then 3
                            when trim(p.method::text) in ('Métodos pouco definidos', 'POORLY_DEFINED')
                                then 4
                            when trim(p.method::text) in ('Métodos desconhecidos ou inexistentes', 'UNKNOWN')
                                then 5
                        end as method_score
                    from projects p
                    where p.planned_start is not null
                      and p.project_type is not null
                ),
                project_complexity as (
                    select
                        project_type,
                        responsible_login,
                        year,
                        month,
                        least(
                            5,
                            greatest(
                                1,
                                ceil((objective_score * method_score)::numeric / 5.0)::int
                            )
                        ) as complexity_score
                    from classified_projects
                    where objective_score is not null
                      and method_score is not null
                )
                select
                    project_type,
                    responsible_login,
                    year,
                    month,
                    complexity_score,
                    count(*)::int as project_count
                from project_complexity
                group by project_type, responsible_login, year, month, complexity_score
                order by year asc, month asc, project_type asc, responsible_login asc, complexity_score asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_type": row["project_type"],
                "responsible_login": row["responsible_login"],
                "year": int(row["year"] or 0),
                "month": int(row["month"] or 0),
                "complexity_score": int(row["complexity_score"] or 0),
                "project_count": int(row["project_count"] or 0),
            }
            for row in rows
        ]

    def list_projects_by_responsible(self) -> list[dict]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                with task_counts as (
                    select
                        t.project_id,
                        count(*)::int as task_count,
                        count(
                            case
                                when upper(replace(trim(t.status::text), ' ', '_')) in ('COMPLETED', 'COMPLETE')
                                    then 1
                            end
                        )::int as completed_task_count
                    from tasks t
                    group by t.project_id
                ),
                classified_projects as (
                    select
                        p.id as project_id,
                        p.name as project_name,
                        p.project_type,
                        coalesce(nullif(trim(p.responsible_login::text), ''), 'Sem responsável') as responsible_login,
                        p.planned_start,
                        p.planned_end,
                        extract(year from p.planned_start)::int as year,
                        extract(month from p.planned_start)::int as month,
                        greatest(coalesce(p.estimated_cost, 0), 0) as estimated_cost,
                        coalesce(tc.task_count, 0)::int as task_count,
                        coalesce(tc.completed_task_count, 0)::int as completed_task_count,
                        case
                            when trim(p.severity::text) in ('Sem gravidade', 'NONE') then 1
                            when trim(p.severity::text) in ('Pouco grave', 'LOW') then 2
                            when trim(p.severity::text) in ('Grave', 'MEDIUM') then 3
                            when trim(p.severity::text) in ('Muito grave', 'HIGH') then 4
                            when trim(p.severity::text) in ('Gravíssimo', 'CRITICAL') then 5
                            else 1
                        end as severity_score,
                        case
                            when trim(p.urgency::text) in ('Pode esperar', 'CAN_WAIT') then 1
                            when trim(p.urgency::text) in ('Pouco urgente', 'LOW') then 2
                            when trim(p.urgency::text) in ('Urgente', 'MEDIUM') then 3
                            when trim(p.urgency::text) in ('Mais rápido possível', 'FAST') then 4
                            when trim(p.urgency::text) in ('Imediatamente', 'IMMEDIATE') then 5
                            else 1
                        end as urgency_score,
                        case
                            when trim(p.trend::text) in ('Não tende a piorar', 'STABLE') then 1
                            when trim(p.trend::text) in ('Piora em longo prazo', 'LONG_TERM') then 2
                            when trim(p.trend::text) in ('Piora em médio prazo', 'MEDIUM_TERM') then 3
                            when trim(p.trend::text) in ('Piora em curto prazo', 'SHORT_TERM') then 4
                            when trim(p.trend::text) in ('Piora rapidamente', 'RAPID') then 5
                            else 1
                        end as trend_score,
                        case
                            when trim(p.objective::text) in ('Objetivo totalmente definido', 'FULLY_DEFINED')
                                then 1
                            when trim(p.objective::text) in ('Objetivo claro com pequenas ambiguidades', 'CLEAR_WITH_AMBIGUITIES')
                                then 2
                            when trim(p.objective::text) in ('Objetivo parcialmente definido', 'PARTIALLY_DEFINED')
                                then 3
                            when trim(p.objective::text) in ('Objetivo pouco claro', 'UNCLEAR')
                                then 4
                            when trim(p.objective::text) in ('Objetivo indefinido ou exploratório', 'UNDEFINED')
                                then 5
                            else 1
                        end as objective_score,
                        case
                            when trim(p.method::text) in ('Métodos totalmente definidos e dominados', 'FULLY_DEFINED')
                                then 1
                            when trim(p.method::text) in (
                                'Métodos conhecidos com pequenas adaptações',
                                'Métodos definidos com pequenas alterações',
                                'KNOWN_WITH_ADAPTATIONS'
                            )
                                then 2
                            when trim(p.method::text) in ('Métodos parcialmente conhecidos', 'PARTIALLY_KNOWN')
                                then 3
                            when trim(p.method::text) in ('Métodos pouco definidos', 'POORLY_DEFINED')
                                then 4
                            when trim(p.method::text) in ('Métodos desconhecidos ou inexistentes', 'UNKNOWN')
                                then 5
                            else 1
                        end as method_score
                    from projects p
                    left join task_counts tc on tc.project_id = p.id
                    where p.planned_start is not null
                      and p.planned_end is not null
                      and p.project_type is not null
                ),
                scored_projects as (
                    select
                        *,
                        severity_score * urgency_score * trend_score as gut_score,
                        least(
                            5,
                            greatest(
                                1,
                                ceil((objective_score * method_score)::numeric / 5.0)::int
                            )
                        ) as complexity_score,
                        case
                            when task_count > 0
                                then round((completed_task_count::numeric / task_count::numeric) * 100.0, 2)
                            else 0
                        end as percent_completed
                    from classified_projects
                )
                select
                    project_id,
                    project_name,
                    project_type,
                    responsible_login,
                    planned_start,
                    planned_end,
                    year,
                    month,
                    estimated_cost,
                    task_count,
                    completed_task_count,
                    percent_completed,
                    gut_score,
                    case
                        when gut_score >= 101 then 1
                        when gut_score >= 76 then 2
                        when gut_score >= 51 then 3
                        when gut_score >= 26 then 4
                        else 5
                    end as priority_level,
                    complexity_score
                from scored_projects
                order by responsible_login asc, year asc, month asc, priority_level asc, project_name asc
                """
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_id": int(row["project_id"]),
                "project_name": row["project_name"],
                "project_type": row["project_type"],
                "responsible_login": row["responsible_login"],
                "planned_start": row["planned_start"],
                "planned_end": row["planned_end"],
                "estimated_cost": float(row["estimated_cost"] or 0.0),
                "task_count": int(row["task_count"] or 0),
                "completed_task_count": int(row["completed_task_count"] or 0),
                "percent_completed": float(row["percent_completed"] or 0.0),
                "gut_score": int(row["gut_score"] or 1),
                "priority_level": int(row["priority_level"] or 5),
                "complexity_score": int(row["complexity_score"] or 1),
                "year": int(row["year"] or 0),
                "month": int(row["month"] or 0),
            }
            for row in rows
        ]

    def list_project_earned_value(self) -> list[dict]:
        planned_hours_sql = _planned_hours_sql("t.planned_start", "t.planned_end")
        planned_progress_sql = _planned_progress_sql("p.planned_start", "p.planned_end")
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                with task_actual_effort as (
                    select
                        t.id as task_id,
                        coalesce(sum(
                            case
                                when te.end_time is not null and te.end_time > te.start_time
                                    then extract(epoch from (te.end_time - te.start_time)) / 3600.0
                                else 0
                            end
                        ), 0) as actual_effort_hours
                    from tasks t
                    left join time_entries te on te.task_id = t.id
                    group by t.id
                ),
                task_values as (
                    select
                        t.project_id,
                        count(*)::int as task_count,
                        count(
                            case
                                when upper(replace(trim(t.status::text), ' ', '_')) in ('COMPLETED', 'COMPLETE')
                                    then 1
                            end
                        )::int as completed_task_count,
                        coalesce(sum(greatest(coalesce(t.cost, 0), 0)), 0) as total_task_cost,
                        coalesce(sum(
                            case
                                when upper(replace(trim(t.status::text), ' ', '_')) in ('COMPLETED', 'COMPLETE')
                                    then greatest(coalesce(t.cost, 0), 0)
                                else 0
                            end
                        ), 0) as completed_task_cost,
                        coalesce(sum(
                            case
                                when t.planned_start is not null
                                  and t.planned_end is not null
                                  and t.planned_end > t.planned_start
                                    then {planned_hours_sql}
                                else 0
                            end
                        ), 0) as planned_effort_hours,
                        coalesce(sum(
                            case
                                when upper(replace(trim(t.status::text), ' ', '_')) in ('COMPLETED', 'COMPLETE')
                                  and t.planned_start is not null
                                  and t.planned_end is not null
                                  and t.planned_end > t.planned_start
                                    then {planned_hours_sql}
                                else 0
                            end
                        ), 0) as completed_planned_effort_hours,
                        coalesce(sum(ta.actual_effort_hours), 0) as actual_effort_hours
                    from tasks t
                    left join task_actual_effort ta on ta.task_id = t.id
                    group by t.project_id
                ),
                project_values as (
                    select
                        p.id as project_id,
                        p.name as project_name,
                        p.project_type,
                        coalesce(nullif(trim(p.responsible_login::text), ''), 'Sem responsável') as responsible_login,
                        extract(year from p.planned_start)::int as year,
                        extract(month from p.planned_start)::int as month,
                        greatest(coalesce(p.estimated_cost, 0), 0) as estimated_cost,
                        coalesce(tv.total_task_cost, 0) as total_task_cost,
                        coalesce(tv.completed_task_cost, 0) as completed_task_cost,
                        coalesce(tv.planned_effort_hours, 0) as planned_effort_hours,
                        coalesce(tv.actual_effort_hours, 0) as actual_effort_hours,
                        coalesce(tv.planned_effort_hours, 0) * %s::numeric as planned_labor_cost,
                        coalesce(tv.actual_effort_hours, 0) * %s::numeric as actual_labor_cost,
                        coalesce(tv.completed_planned_effort_hours, 0) * %s::numeric as completed_planned_labor_cost,
                        coalesce(tv.task_count, 0)::int as task_count,
                        coalesce(tv.completed_task_count, 0)::int as completed_task_count,
                        (
                            case
                                when greatest(coalesce(p.estimated_cost, 0), 0) > 0
                                    then greatest(coalesce(p.estimated_cost, 0), 0)
                                else coalesce(tv.total_task_cost, 0)
                            end
                            + coalesce(tv.planned_effort_hours, 0) * %s::numeric
                        ) as baseline_value,
                        {planned_progress_sql} as planned_progress
                    from projects p
                    left join task_values tv on tv.project_id = p.id
                    where p.planned_start is not null
                      and p.project_type is not null
                )
                select
                    project_id,
                    project_name,
                    project_type,
                    responsible_login,
                    year,
                    month,
                    estimated_cost,
                    total_task_cost,
                    completed_task_cost + completed_planned_labor_cost as earned_value,
                    planned_effort_hours,
                    actual_effort_hours,
                    planned_labor_cost,
                    actual_labor_cost,
                    total_task_cost + actual_labor_cost as actual_cost,
                    task_count,
                    completed_task_count,
                    baseline_value * greatest(0, least(1, coalesce(planned_progress, 0))) as planned_value
                from project_values
                where baseline_value > 0
                   or (completed_task_cost + completed_planned_labor_cost) > 0
                   or (total_task_cost + actual_labor_cost) > 0
                order by year asc, month asc, project_type asc, responsible_login asc, project_name asc
                """,
                (
                    ENGINEERING_PROCESS_HOURLY_RATE,
                    ENGINEERING_PROCESS_HOURLY_RATE,
                    ENGINEERING_PROCESS_HOURLY_RATE,
                    ENGINEERING_PROCESS_HOURLY_RATE,
                ),
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_id": int(row["project_id"]),
                "project_name": row["project_name"],
                "project_type": row["project_type"],
                "responsible_login": row["responsible_login"],
                "year": int(row["year"] or 0),
                "month": int(row["month"] or 0),
                "estimated_cost": float(row["estimated_cost"] or 0.0),
                "planned_value": float(row["planned_value"] or 0.0),
                "earned_value": float(row["earned_value"] or 0.0),
                "total_task_cost": float(row["total_task_cost"] or 0.0),
                "planned_effort_hours": float(row["planned_effort_hours"] or 0.0),
                "actual_effort_hours": float(row["actual_effort_hours"] or 0.0),
                "planned_labor_cost": float(row["planned_labor_cost"] or 0.0),
                "actual_labor_cost": float(row["actual_labor_cost"] or 0.0),
                "actual_cost": float(row["actual_cost"] or 0.0),
                "task_count": int(row["task_count"] or 0),
                "completed_task_count": int(row["completed_task_count"] or 0),
            }
            for row in rows
        ]

    def list_project_effort_deviation(self) -> list[dict]:
        planned_hours_sql = _planned_hours_sql("t.planned_start", "t.planned_end")
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                with task_actual_effort as (
                    select
                        t.id as task_id,
                        coalesce(sum(
                            case
                                when te.end_time is not null and te.end_time > te.start_time
                                    then extract(epoch from (te.end_time - te.start_time)) / 3600.0
                                else 0
                            end
                        ), 0) as actual_effort_hours
                    from tasks t
                    left join time_entries te on te.task_id = t.id
                    group by t.id
                ),
                task_effort as (
                    select
                        p.project_type,
                        coalesce(nullif(trim(p.responsible_login::text), ''), 'Sem responsável') as responsible_login,
                        extract(year from t.planned_start)::int as year,
                        extract(month from t.planned_start)::int as month,
                        {planned_hours_sql} as planned_effort_hours,
                        coalesce(ta.actual_effort_hours, 0) as actual_effort_hours
                    from projects p
                    join tasks t on t.project_id = p.id
                    left join task_actual_effort ta on ta.task_id = t.id
                    where p.project_type is not null
                      and t.planned_start is not null
                      and t.planned_end is not null
                      and t.planned_end > t.planned_start
                )
                select
                    project_type,
                    responsible_login,
                    year,
                    month,
                    count(*)::int as task_count,
                    coalesce(sum(planned_effort_hours), 0) as planned_effort_hours,
                    coalesce(sum(actual_effort_hours), 0) as actual_effort_hours,
                    coalesce(sum(planned_effort_hours), 0) * %s::numeric as planned_labor_cost,
                    coalesce(sum(actual_effort_hours), 0) * %s::numeric as actual_labor_cost
                from task_effort
                where actual_effort_hours > 0
                group by project_type, responsible_login, year, month
                order by year asc, month asc, project_type asc, responsible_login asc
                """,
                (
                    ENGINEERING_PROCESS_HOURLY_RATE,
                    ENGINEERING_PROCESS_HOURLY_RATE,
                ),
            )
            rows = cur.fetchall() or []

        return [
            {
                "project_type": row["project_type"],
                "responsible_login": row["responsible_login"],
                "year": int(row["year"] or 0),
                "month": int(row["month"] or 0),
                "task_count": int(row["task_count"] or 0),
                "planned_effort_hours": float(row["planned_effort_hours"] or 0.0),
                "actual_effort_hours": float(row["actual_effort_hours"] or 0.0),
                "planned_labor_cost": float(row["planned_labor_cost"] or 0.0),
                "actual_labor_cost": float(row["actual_labor_cost"] or 0.0),
                "labor_cost_deviation": float(
                    (row["actual_labor_cost"] or 0.0) - (row["planned_labor_cost"] or 0.0)
                ),
            }
            for row in rows
        ]

    def list_new_process_time_by_month(self) -> list[dict]:
        grouped: dict[tuple[str, int, int], dict] = {}

        def add_days(
            responsible_label: str,
            year: int,
            month: int,
            *,
            project_days: float = 0.0,
            routine_days: float = 0.0,
        ) -> None:
            key = (responsible_label, year, month)
            current = grouped.setdefault(
                key,
                {
                    "responsible_label": responsible_label,
                    "year": year,
                    "month": month,
                    "project_days": 0.0,
                    "routine_days": 0.0,
                },
            )
            current["project_days"] += project_days
            current["routine_days"] += routine_days

        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select
                    coalesce(nullif(trim(p.responsible_login::text), ''), 'Sem responsável') as responsible_label,
                    extract(year from p.planned_start)::int as year,
                    extract(month from p.planned_start)::int as month,
                    sum(extract(epoch from (te.end_time - te.start_time))) / 86400.0 as project_days
                from projects p
                join tasks t on t.project_id = p.id
                join time_entries te on te.task_id = t.id
                where te.end_time is not null
                  and te.end_time > te.start_time
                  and p.planned_start is not null
                  and upper(trim(coalesce(p.process_classification::text, ''))) in ('PROCESSOS NOVOS', 'NEW')
                group by responsible_label, year, month
                having sum(extract(epoch from (te.end_time - te.start_time))) > 0
                """
            )
            for row in cur.fetchall() or []:
                add_days(
                    str(row["responsible_label"] or "Sem responsável"),
                    int(row["year"] or 0),
                    int(row["month"] or 0),
                    project_days=float(row["project_days"] or 0.0),
                )

            cur.execute(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'atividades'
                """
            )
            columns = {row["column_name"] for row in (cur.fetchall() or [])}

            if "tipo_atividade" in columns:
                user_expr = (
                    "coalesce(nullif(trim(user_id::text), ''), 'Sem usuário')"
                    if "user_id" in columns
                    else "'Sem usuário'"
                )
                user_fallback_expr = f"""
                    case
                        when length({user_expr}) > 12
                            then 'Usuário ' || left({user_expr}, 4) || '...' || right({user_expr}, 4)
                        else {user_expr}
                    end
                """
                user_label_expr = (
                    f"coalesce(nullif(trim(responsavel::text), ''), {user_fallback_expr})"
                    if "responsavel" in columns
                    else user_fallback_expr
                )

                def year_value_expr(column_name: str) -> str:
                    return f"""
                        case
                            when trim({column_name}::text) ~ '^[0-9]+(\\.[0-9]+)?$'
                                then floor({column_name}::numeric)::int
                        end
                    """

                def month_value_expr(column_name: str) -> str:
                    return f"""
                        case
                            when trim({column_name}::text) ~ '^[0-9]+(\\.[0-9]+)?$'
                                then floor({column_name}::numeric)::int
                            when upper(left(trim({column_name}::text), 3)) = 'JAN' then 1
                            when upper(left(trim({column_name}::text), 3)) = 'FEV' then 2
                            when upper(left(trim({column_name}::text), 3)) = 'MAR' then 3
                            when upper(left(trim({column_name}::text), 3)) = 'ABR' then 4
                            when upper(left(trim({column_name}::text), 3)) = 'MAI' then 5
                            when upper(left(trim({column_name}::text), 3)) = 'JUN' then 6
                            when upper(left(trim({column_name}::text), 3)) = 'JUL' then 7
                            when upper(left(trim({column_name}::text), 3)) = 'AGO' then 8
                            when upper(left(trim({column_name}::text), 3)) = 'SET' then 9
                            when upper(left(trim({column_name}::text), 3)) = 'OUT' then 10
                            when upper(left(trim({column_name}::text), 3)) = 'NOV' then 11
                            when upper(left(trim({column_name}::text), 3)) = 'DEZ' then 12
                        end
                    """

                year_parts: list[str] = []
                month_parts: list[str] = []
                worked_hour_rules: list[str] = []

                if "ano" in columns:
                    year_parts.append(year_value_expr("ano"))
                if "inicio" in columns:
                    year_parts.append("extract(year from inicio)::int")

                if "mes" in columns:
                    month_parts.append(month_value_expr("mes"))
                if "mes_nome" in columns:
                    month_parts.append(month_value_expr("mes_nome"))
                if "inicio" in columns:
                    month_parts.append("extract(month from inicio)::int")

                if "horas_trabalhadas" in columns:
                    worked_hour_rules.append(
                        """
                        when horas_trabalhadas is not null
                             and replace(trim(horas_trabalhadas::text), ',', '.') ~ '^[0-9]+(\\.[0-9]+)?$'
                             and replace(trim(horas_trabalhadas::text), ',', '.')::numeric > 0
                            then replace(trim(horas_trabalhadas::text), ',', '.')::numeric
                        """
                    )
                if "inicio" in columns and "fim" in columns:
                    worked_hour_rules.append(
                        """
                        when fim is not null and inicio is not null and fim > inicio
                            then extract(epoch from (fim - inicio)) / 3600.0
                        """
                    )

                if year_parts and month_parts and worked_hour_rules:
                    year_expr = (
                        year_parts[0]
                        if len(year_parts) == 1
                        else f"coalesce({', '.join(year_parts)})"
                    )
                    month_expr = (
                        month_parts[0]
                        if len(month_parts) == 1
                        else f"coalesce({', '.join(month_parts)})"
                    )
                    worked_hours_expr = "case " + " ".join(worked_hour_rules) + " else 0 end"

                    cur.execute(
                        f"""
                        with routine_hours as (
                            select
                                {user_label_expr} as responsible_label,
                                {year_expr} as year,
                                {month_expr} as month,
                                {worked_hours_expr} as worked_hours
                            from atividades
                            where trim(tipo_atividade::text) in (
                                'Reuniões sobre Processos Novos',
                                'Análise de Processos Novos'
                            )
                        )
                        select
                            responsible_label,
                            year,
                            month,
                            sum(worked_hours) / 24.0 as routine_days
                        from routine_hours
                        where year is not null
                          and month between 1 and 12
                        group by responsible_label, year, month
                        having sum(worked_hours) > 0
                        """
                    )
                    for row in cur.fetchall() or []:
                        add_days(
                            str(row["responsible_label"] or "Sem responsável"),
                            int(row["year"] or 0),
                            int(row["month"] or 0),
                            routine_days=float(row["routine_days"] or 0.0),
                        )

        rows = list(grouped.values())
        rows.sort(
            key=lambda item: (
                item["year"],
                item["month"],
                item["responsible_label"],
            )
        )
        return rows
