#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Importa a carga A3 2026 de projetos no Supabase/Postgres.

Uso seguro padrao, sem escrita no banco:
    python automacoes/importar_a3_2026_supabase.py --user-id <supabase-user-id>

Importacao real:
    python automacoes/importar_a3_2026_supabase.py --user-id <supabase-user-id> --commit
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automacoes.importar_a3_supabase import (
    MigrationError,
    ROOT_DIR,
    days_to_seconds,
    load_dotenv_if_available,
    map_method,
    map_objective,
    map_project_type,
    map_severity,
    map_task_status,
    map_trend,
    map_urgency,
    normalize_key,
    normalize_spaces,
    parse_excel_datetime,
    strip_numbered_label,
    to_float,
    to_positive_float,
    to_text,
    write_json,
)
from automacoes.file_validation import validate_input_file
from domain.responsible import normalize_responsible_name

DEFAULT_WORKBOOK = ROOT_DIR / "A3 - Gerenciamento de Projetos (2026).xlsx"
DEFAULT_REPORT = Path(__file__).with_name("import_a3_2026_report.json")
PROJECT_START_COLUMN = "DATA INÍCIO PLANEJ"
PROJECT_END_COLUMN = "DATA FIM PLANEJ"
TASK_START_COLUMN = "DATA INÍCIO PLANEJ"
TASK_END_COLUMN = "DATA FIM DO PLANEJ"
SOLDAGEM_PROJECT_NAME = "Projeto de Normatização do Processo de Soldagem"
SOLDAGEM_PROJECT_KEY = normalize_key(SOLDAGEM_PROJECT_NAME)
EXTERNAL_PROJECTS = {
    SOLDAGEM_PROJECT_KEY: {
        "name": SOLDAGEM_PROJECT_NAME,
        "year": 2025,
    }
}


@dataclass(frozen=True)
class Project2026Record:
    source_key: str
    name: str
    project_type: str
    process_classification: str | None
    responsible_login: str
    fte: float
    planned_start: datetime
    planned_end: datetime
    severity: str
    urgency: str
    trend: str
    objective: str
    method: str
    estimated_cost: float


@dataclass(frozen=True)
class Task2026Record:
    source_key: str
    source_project_key: str
    source_project_name: str
    name: str
    planned_start: datetime
    planned_end: datetime
    cost: float
    status: str
    actual_seconds: int
    actual_start: datetime | None


@dataclass(frozen=True)
class Import2026Records:
    projects: list[Project2026Record]
    tasks: list[Task2026Record]
    skipped_projects: list[dict[str, Any]]
    skipped_tasks: list[dict[str, Any]]


def has_ref_error(*values: Any) -> bool:
    return any(normalize_key(value) == "ref" for value in values)


def project_type_2026(value: Any) -> tuple[str, str | None]:
    raw_key = normalize_key(strip_numbered_label(value))
    if raw_key == "normatizacao dos processos":
        return "NORMATIZACAO", None
    return map_project_type(value), None


def build_task_name(task_name: Any, subtask_name: Any) -> str:
    task = to_text(task_name)
    subtask = to_text(subtask_name)
    if subtask and normalize_key(subtask) != "na":
        return f"{task} - {subtask}"
    return task


def map_task_status_2026(percent_done: Any, actual_seconds: int) -> str:
    return map_task_status("", actual_seconds, percent_done)


def read_excel_records_2026(workbook_path: Path, year: int = 2026) -> Import2026Records:
    try:
        import pandas as pd
    except ImportError as exc:
        raise MigrationError(
            "Dependencia ausente: instale pandas e openpyxl com `pip install -r requirements.txt`."
        ) from exc

    try:
        workbook_path = validate_input_file(
            workbook_path,
            allowed_suffixes={".xlsx"},
            description="Planilha",
        )
    except (FileNotFoundError, ValueError) as exc:
        raise MigrationError(str(exc)) from exc

    def read_sheet(sheet_name: str) -> list[dict[str, Any]]:
        try:
            frame = pd.read_excel(workbook_path, sheet_name=sheet_name, engine="openpyxl")
        except ImportError as exc:
            raise MigrationError(
                "Dependencia ausente: instale openpyxl com `pip install -r requirements.txt`."
            ) from exc
        except ValueError as exc:
            raise MigrationError(f"Aba obrigatoria nao encontrada: {sheet_name}") from exc

        columns = [normalize_spaces(col) for col in frame.columns]
        records: list[dict[str, Any]] = []
        for index, row in frame.iterrows():
            record: dict[str, Any] = {"_row_number": int(index) + 2}
            for column, value in zip(columns, row.tolist(), strict=False):
                record[column] = None if pd.isna(value) else value
            if any(value not in (None, "") for key, value in record.items() if key != "_row_number"):
                records.append(record)
        return records

    return build_records_2026(
        read_sheet("PROJETOS_2026"),
        read_sheet("TAREFAS_2026"),
        year=year,
    )


def build_records_2026(
    project_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    *,
    year: int = 2026,
) -> Import2026Records:
    projects: list[Project2026Record] = []
    tasks: list[Task2026Record] = []
    skipped_projects: list[dict[str, Any]] = []
    skipped_tasks: list[dict[str, Any]] = []
    projects_by_key: dict[str, Project2026Record] = {}

    for index, row in enumerate(project_rows, start=2):
        row_number = int(row.get("_row_number") or index)
        name = to_text(row.get("PROJETOS"))
        if not name:
            continue

        source_key = normalize_key(name)
        start_value = row.get(PROJECT_START_COLUMN)
        end_value = row.get(PROJECT_END_COLUMN)
        if has_ref_error(start_value, end_value):
            skipped_projects.append(
                {"row": row_number, "name": name, "reason": "ref_error"}
            )
            continue

        planned_start = parse_excel_datetime(start_value)
        planned_end = parse_excel_datetime(end_value)
        if planned_start is None or planned_end is None:
            skipped_projects.append(
                {"row": row_number, "name": name, "reason": "invalid_project_dates"}
            )
            continue
        if planned_start.year != year:
            skipped_projects.append(
                {"row": row_number, "name": name, "reason": "planned_start_outside_year"}
            )
            continue
        if planned_end < planned_start:
            planned_end = planned_start
        if source_key in projects_by_key:
            skipped_projects.append(
                {"row": row_number, "name": name, "reason": "duplicate_project_name"}
            )
            continue

        try:
            project_type, process_classification = project_type_2026(
                row.get("TIPO DE PROJETOS")
            )
        except MigrationError as exc:
            skipped_projects.append(
                {"row": row_number, "name": name, "reason": str(exc)}
            )
            continue

        project = Project2026Record(
            source_key=source_key,
            name=name,
            project_type=project_type,
            process_classification=process_classification,
            responsible_login=normalize_responsible_name(
                to_text(row.get("RESPONSÁVEL")) or "nao_informado"
            ),
            fte=to_positive_float(row.get("FTes"), 1.0),
            planned_start=planned_start,
            planned_end=planned_end,
            severity=map_severity(row.get("GRAVIDADE")),
            urgency=map_urgency(row.get("URGÊNCIA")),
            trend=map_trend(row.get("TENDêNCIA")),
            objective=map_objective(row.get("OBJETIVOS")),
            method=map_method(row.get("MÉTODOS")),
            estimated_cost=to_float(row.get("Valor previsto"), 0.0),
        )
        projects.append(project)
        projects_by_key[source_key] = project

    seen_task_names: set[tuple[str, str]] = set()
    for index, row in enumerate(task_rows, start=2):
        row_number = int(row.get("_row_number") or index)
        project_name = to_text(row.get("PROJETO"))
        raw_task_name = to_text(row.get("TAREFA"))
        if not project_name and not raw_task_name:
            continue
        if not project_name or not raw_task_name:
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": raw_task_name,
                    "reason": "missing_task_reference",
                }
            )
            continue

        project_key = normalize_key(project_name)
        project = projects_by_key.get(project_key)
        if project is None and project_key not in EXTERNAL_PROJECTS:
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": build_task_name(raw_task_name, row.get("SUBTAREFA")),
                    "reason": "project_not_imported",
                }
            )
            continue

        task_name = build_task_name(raw_task_name, row.get("SUBTAREFA"))
        start_value = row.get(TASK_START_COLUMN)
        end_value = row.get(TASK_END_COLUMN)
        if has_ref_error(start_value, end_value):
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": task_name,
                    "reason": "ref_error",
                }
            )
            continue

        planned_start = parse_excel_datetime(start_value)
        planned_end = parse_excel_datetime(end_value)
        if planned_start is None or planned_end is None:
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": task_name,
                    "reason": "invalid_task_dates",
                }
            )
            continue
        if planned_start.year != year:
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": task_name,
                    "reason": "planned_start_outside_year",
                }
            )
            continue
        if planned_end < planned_start:
            planned_end = planned_start

        seen_key = (project_key, task_name)
        if seen_key in seen_task_names:
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": task_name,
                    "reason": "duplicate_task_name",
                }
            )
            continue
        seen_task_names.add(seen_key)

        actual_seconds = days_to_seconds(row.get("DIAS REAIS"))
        actual_start = None
        if actual_seconds > 0:
            actual_start = parse_excel_datetime(row.get("DATA INÍCIO REAL"))

        tasks.append(
            Task2026Record(
                source_key=f"{row_number}:{project_key}:{task_name}",
                source_project_key=project_key,
                source_project_name=project.name if project else project_name,
                name=task_name,
                planned_start=planned_start,
                planned_end=planned_end,
                cost=to_float(row.get("Valor previsto"), 0.0),
                status=map_task_status_2026(row.get("PERCENTUAL REALIZADO"), actual_seconds),
                actual_seconds=actual_seconds,
                actual_start=actual_start,
            )
        )

    return Import2026Records(
        projects=projects,
        tasks=tasks,
        skipped_projects=skipped_projects,
        skipped_tasks=skipped_tasks,
    )


def year_bounds(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1), datetime(year + 1, 1, 1)


class SupabaseImport2026Writer:
    def __init__(self, database_url: str):
        import psycopg2

        self.conn = psycopg2.connect(database_url, connect_timeout=10)

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def find_project_by_name_and_year(
        self,
        user_id: str,
        name: str,
        year: int,
    ) -> int | None:
        start, end = year_bounds(year)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select id
                from projects
                where user_id = %s
                  and lower(trim(name)) = lower(trim(%s))
                  and planned_start >= %s
                  and planned_start < %s
                order by id
                """,
                (user_id, name, start, end),
            )
            rows = cur.fetchall()

        if len(rows) > 1:
            raise MigrationError(
                f"Projeto ambiguo para user_id={user_id}, nome={name!r}, ano={year}."
            )
        if not rows:
            return None
        return int(rows[0][0])

    def find_task_by_name(self, project_id: int, user_id: str, name: str) -> int | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select id
                from tasks
                where project_id = %s
                  and user_id = %s
                  and name = %s
                order by id
                """,
                (project_id, user_id, name),
            )
            rows = cur.fetchall()

        if len(rows) > 1:
            raise MigrationError(
                f"Tarefa ambigua para project_id={project_id}, nome={name!r}."
            )
        if not rows:
            return None
        return int(rows[0][0])

    def time_entry_exists(self, task_id: int, task: Task2026Record) -> bool:
        if task.actual_start is None or task.actual_seconds <= 0:
            return False
        end_time = task.actual_start + timedelta(seconds=task.actual_seconds)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select 1
                from time_entries
                where task_id = %s
                  and start_time = %s
                  and end_time = %s
                """,
                (task_id, task.actual_start, end_time),
            )
            return cur.fetchone() is not None

    def insert_project(self, user_id: str, project: Project2026Record) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into projects (
                    user_id, name, project_type, process_classification,
                    responsible_login, fte, planned_start, planned_end,
                    severity, urgency, trend, objective, method, estimated_cost
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                returning id
                """,
                (
                    user_id,
                    project.name,
                    project.project_type,
                    project.process_classification,
                    project.responsible_login,
                    project.fte,
                    project.planned_start,
                    project.planned_end,
                    project.severity,
                    project.urgency,
                    project.trend,
                    project.objective,
                    project.method,
                    project.estimated_cost,
                ),
            )
            return int(cur.fetchone()[0])

    def insert_task(self, user_id: str, project_id: int, task: Task2026Record) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into tasks (
                    project_id, user_id, name, planned_start, planned_end, cost, status
                )
                values (%s,%s,%s,%s,%s,%s,%s)
                returning id
                """,
                (
                    project_id,
                    user_id,
                    task.name,
                    task.planned_start,
                    task.planned_end,
                    task.cost,
                    task.status,
                ),
            )
            return int(cur.fetchone()[0])

    def insert_time_entry(self, task_id: int, task: Task2026Record) -> int:
        if task.actual_start is None or task.actual_seconds <= 0:
            raise MigrationError("Time entry precisa de inicio e duracao positiva.")
        end_time = task.actual_start + timedelta(seconds=task.actual_seconds)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into time_entries (task_id, start_time, end_time)
                values (%s,%s,%s)
                returning id
                """,
                (task_id, task.actual_start, end_time),
            )
            return int(cur.fetchone()[0])


def time_entries_ready(records: Import2026Records) -> int:
    return sum(
        1
        for task in records.tasks
        if task.actual_seconds > 0 and task.actual_start is not None
    )


def external_project_keys(records: Import2026Records) -> set[str]:
    project_keys = {project.source_key for project in records.projects}
    return {
        task.source_project_key
        for task in records.tasks
        if task.source_project_key not in project_keys
    }


def build_initial_report(args: argparse.Namespace, records: Import2026Records) -> dict[str, Any]:
    time_entries = time_entries_ready(records)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "commit" if args.commit else "dry-run",
        "workbook": str(args.workbook),
        "year": args.year,
        "user_id": args.user_id,
        "external_projects_required": [
            EXTERNAL_PROJECTS[key]
            for key in sorted(external_project_keys(records))
            if key in EXTERNAL_PROJECTS
        ],
        "counts": {
            "projects_ready": len(records.projects),
            "tasks_ready": len(records.tasks),
            "time_entries_ready": time_entries,
            "projects_skipped": len(records.skipped_projects),
            "tasks_skipped": len(records.skipped_tasks),
            "database_checked": False,
            "external_projects_resolved": 0,
            "projects_existing": 0,
            "projects_would_insert": len(records.projects),
            "projects_inserted": 0,
            "tasks_existing": 0,
            "tasks_would_insert": len(records.tasks),
            "tasks_inserted": 0,
            "time_entries_existing": 0,
            "time_entries_would_insert": time_entries,
            "time_entries_inserted": 0,
        },
        "skipped_projects": records.skipped_projects,
        "skipped_tasks": records.skipped_tasks,
    }


def resolve_external_project_ids(
    writer: SupabaseImport2026Writer,
    user_id: str,
    records: Import2026Records,
) -> dict[str, int]:
    project_ids: dict[str, int] = {}
    for key in sorted(external_project_keys(records)):
        config = EXTERNAL_PROJECTS.get(key)
        if config is None:
            raise MigrationError(f"Projeto externo nao configurado para chave {key!r}.")
        project_id = writer.find_project_by_name_and_year(
            user_id,
            str(config["name"]),
            int(config["year"]),
        )
        if project_id is None:
            raise MigrationError(
                "Projeto externo nao encontrado no Supabase: "
                f"{config['name']!r}, ano planejado {config['year']}."
            )
        project_ids[key] = project_id
    return project_ids


def resolve_import_project_ids(
    writer: SupabaseImport2026Writer,
    user_id: str,
    year: int,
    records: Import2026Records,
) -> tuple[dict[str, int], int]:
    project_ids: dict[str, int] = {}
    existing = 0
    for project in records.projects:
        project_id = writer.find_project_by_name_and_year(user_id, project.name, year)
        if project_id is not None:
            project_ids[project.source_key] = project_id
            existing += 1
    return project_ids, existing


def update_dry_run_database_counts(
    writer: SupabaseImport2026Writer,
    args: argparse.Namespace,
    records: Import2026Records,
    counts: dict[str, Any],
) -> None:
    project_db_ids = resolve_external_project_ids(writer, args.user_id, records)
    import_project_ids, projects_existing = resolve_import_project_ids(
        writer,
        args.user_id,
        args.year,
        records,
    )
    project_db_ids.update(import_project_ids)

    tasks_existing = 0
    time_entries_existing = 0
    tasks_would_insert = 0
    time_entries_would_insert = 0
    for task in records.tasks:
        project_id = project_db_ids.get(task.source_project_key)
        if project_id is None:
            tasks_would_insert += 1
            if task.actual_seconds > 0 and task.actual_start is not None:
                time_entries_would_insert += 1
            continue

        task_id = writer.find_task_by_name(project_id, args.user_id, task.name)
        if task_id is None:
            tasks_would_insert += 1
            if task.actual_seconds > 0 and task.actual_start is not None:
                time_entries_would_insert += 1
            continue

        tasks_existing += 1
        if task.actual_seconds > 0 and task.actual_start is not None:
            if writer.time_entry_exists(task_id, task):
                time_entries_existing += 1
            else:
                time_entries_would_insert += 1

    counts["database_checked"] = True
    counts["external_projects_resolved"] = len(external_project_keys(records))
    counts["projects_existing"] = projects_existing
    counts["projects_would_insert"] = len(records.projects) - projects_existing
    counts["tasks_existing"] = tasks_existing
    counts["tasks_would_insert"] = tasks_would_insert
    counts["time_entries_existing"] = time_entries_existing
    counts["time_entries_would_insert"] = time_entries_would_insert


def run_import(
    args: argparse.Namespace,
    *,
    writer_cls: type[SupabaseImport2026Writer] = SupabaseImport2026Writer,
) -> dict[str, Any]:
    records = read_excel_records_2026(args.workbook, args.year)
    report = build_initial_report(args, records)
    counts = report["counts"]

    database_url = os.getenv("DATABASE_URL")
    if not args.commit:
        if database_url:
            writer = None
            try:
                writer = writer_cls(database_url)
                update_dry_run_database_counts(writer, args, records, counts)
            except Exception as exc:
                report["database_check_error"] = str(exc)
            finally:
                if writer is not None:
                    writer.close()
        write_json(args.report, report)
        return report

    if not database_url:
        raise MigrationError("DATABASE_URL nao definida. Configure no .env ou no ambiente.")
    if not records.projects and not records.tasks:
        raise MigrationError("Nenhum registro valido encontrado para importar.")

    writer = writer_cls(database_url)
    try:
        project_db_ids = resolve_external_project_ids(writer, args.user_id, records)
        import_project_ids, projects_existing = resolve_import_project_ids(
            writer,
            args.user_id,
            args.year,
            records,
        )
        project_db_ids.update(import_project_ids)
        counts["external_projects_resolved"] = len(external_project_keys(records))
        counts["projects_existing"] = projects_existing

        for project in records.projects:
            if project.source_key in project_db_ids:
                continue
            project_id = writer.insert_project(args.user_id, project)
            project_db_ids[project.source_key] = project_id
            counts["projects_inserted"] += 1

        for task in records.tasks:
            project_id = project_db_ids.get(task.source_project_key)
            if project_id is None:
                report.setdefault("runtime_skipped_tasks", []).append(
                    {
                        "source_key": task.source_key,
                        "project": task.source_project_name,
                        "name": task.name,
                        "reason": "project_id_not_available",
                    }
                )
                continue

            task_id = writer.find_task_by_name(project_id, args.user_id, task.name)
            if task_id is not None:
                counts["tasks_existing"] += 1
            else:
                task_id = writer.insert_task(args.user_id, project_id, task)
                counts["tasks_inserted"] += 1

            if task.actual_seconds <= 0 or task.actual_start is None:
                continue

            if writer.time_entry_exists(task_id, task):
                counts["time_entries_existing"] += 1
                continue

            writer.insert_time_entry(task_id, task)
            counts["time_entries_inserted"] += 1

        writer.commit()
    except Exception:
        writer.rollback()
        raise
    finally:
        writer.close()

    write_json(args.report, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa PROJETOS_2026 e TAREFAS_2026 da A3 para Supabase."
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_WORKBOOK,
        help=f"Caminho da planilha .xlsx. Padrao: {DEFAULT_WORKBOOK}",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("SUPABASE_USER_ID"),
        help="User ID do Supabase. Tambem pode vir de SUPABASE_USER_ID.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Ano de planned_start que sera importado. Padrao: 2026.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Relatorio JSON de execucao. Padrao: {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Grava no Supabase. Sem esta flag, executa apenas dry-run.",
    )
    args = parser.parse_args(argv)
    if not args.user_id:
        parser.error("informe --user-id ou configure SUPABASE_USER_ID")
    args.workbook = args.workbook.resolve()
    args.report = args.report.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_available()
    args = parse_args(argv)
    try:
        report = run_import(args)
    except MigrationError as exc:
        print(f"Erro de migracao: {exc}")
        return 2
    except Exception as exc:  # pragma: no cover - mantem stack curta para uso manual.
        print(f"Erro inesperado: {exc}")
        return 1

    counts = report["counts"]
    print(f"Modo: {report['mode']}")
    print(f"Ano: {report['year']}")
    print(f"Projetos prontos: {counts['projects_ready']}")
    print(f"Tarefas prontas: {counts['tasks_ready']}")
    print(f"Time entries prontos: {counts['time_entries_ready']}")
    print(f"Projetos pulados: {counts['projects_skipped']}")
    print(f"Tarefas puladas: {counts['tasks_skipped']}")
    if report["mode"] == "dry-run":
        print(f"Projetos que seriam inseridos: {counts['projects_would_insert']}")
        print(f"Tarefas que seriam inseridas: {counts['tasks_would_insert']}")
        print(f"Time entries que seriam inseridos: {counts['time_entries_would_insert']}")
        if counts["database_checked"]:
            print(f"Projetos ja existentes: {counts['projects_existing']}")
            print(f"Tarefas ja existentes: {counts['tasks_existing']}")
            print(f"Time entries ja existentes: {counts['time_entries_existing']}")
        elif report.get("database_check_error"):
            print("Conferencia no banco falhou; veja o relatorio.")
    else:
        print(f"Projetos ja existentes: {counts['projects_existing']}")
        print(f"Projetos inseridos: {counts['projects_inserted']}")
        print(f"Tarefas ja existentes: {counts['tasks_existing']}")
        print(f"Tarefas inseridas: {counts['tasks_inserted']}")
        print(f"Time entries ja existentes: {counts['time_entries_existing']}")
        print(f"Time entries inseridos: {counts['time_entries_inserted']}")
    print(f"Relatorio: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
