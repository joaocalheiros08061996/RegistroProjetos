#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Substitui a carga A3 2025 de projetos no Supabase/Postgres.

Uso seguro padrao, sem escrita no banco:
    python automacoes/substituir_a3_2025_supabase.py --user-id <supabase-user-id>

Substituicao real:
    python automacoes/substituir_a3_2025_supabase.py --user-id <supabase-user-id> --commit
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

DEFAULT_WORKBOOK = ROOT_DIR / "A3 - Gerenciamento de Projetos (2025).xlsx"
DEFAULT_REPORT = Path(__file__).with_name("substituir_a3_2025_report.json")
PROCESS_CLASSIFICATION_EXISTING = "Processos existentes"
PROCESS_CLASSIFICATION_NEW = "Processos novos"
PROJECT_START_COLUMN = "DATA INÍCIO PLANEJ"
PROJECT_END_COLUMN = "DATA FIM PLANEJ"
TASK_START_COLUMN = "DATA INÍCIO PLANEJ"
TASK_END_COLUMN = "DATA FIM DO PLANEJ"


@dataclass(frozen=True)
class Project2025Record:
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
class Task2025Record:
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
class ReplacementRecords:
    projects: list[Project2025Record]
    tasks: list[Task2025Record]
    skipped_projects: list[dict[str, Any]]
    skipped_tasks: list[dict[str, Any]]


def has_ref_error(*values: Any) -> bool:
    return any(normalize_key(value) == "ref" for value in values)


def project_type_2025(value: Any) -> tuple[str, str | None]:
    raw_key = normalize_key(strip_numbered_label(value))
    if raw_key in {
        "melhoria",
        "melhoria continua dos processos",
        "melhoria de proc existentes",
        "melhoria de processos existentes",
    }:
        return "MELHORIA", PROCESS_CLASSIFICATION_EXISTING
    if raw_key in {
        "melhoria proc novos",
        "melhoria de proc novos",
        "melhoria de processos novos",
    }:
        return "MELHORIA_PROC_NOVOS", PROCESS_CLASSIFICATION_NEW
    if raw_key == "normatizacao dos processos":
        return "NORMATIZACAO", None
    return map_project_type(value), None


def build_task_name(task_name: Any, subtask_name: Any) -> str:
    task = to_text(task_name)
    subtask = to_text(subtask_name)
    if subtask and normalize_key(subtask) != "na":
        return f"{task} - {subtask}"
    return task


def map_task_status_2025(percent_done: Any, actual_seconds: int) -> str:
    return map_task_status("", actual_seconds, percent_done)


def read_excel_records_2025(workbook_path: Path, year: int = 2025) -> ReplacementRecords:
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

    return build_records_2025(
        read_sheet("PROJETOS_2025"),
        read_sheet("TAREFAS_2025"),
        year=year,
    )


def build_records_2025(
    project_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    *,
    year: int = 2025,
) -> ReplacementRecords:
    projects: list[Project2025Record] = []
    tasks: list[Task2025Record] = []
    skipped_projects: list[dict[str, Any]] = []
    skipped_tasks: list[dict[str, Any]] = []
    projects_by_key: dict[str, Project2025Record] = {}

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
            project_type, process_classification = project_type_2025(
                row.get("TIPO DE PROJETOS")
            )
        except MigrationError as exc:
            skipped_projects.append(
                {"row": row_number, "name": name, "reason": str(exc)}
            )
            continue

        project = Project2025Record(
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
        task_name = build_task_name(raw_task_name, row.get("SUBTAREFA"))
        if project is None:
            skipped_tasks.append(
                {
                    "row": row_number,
                    "project": project_name,
                    "name": task_name,
                    "reason": "project_not_imported",
                }
            )
            continue

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

        seen_key = (project.source_key, task_name)
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
            Task2025Record(
                source_key=f"{row_number}:{project.source_key}:{task_name}",
                source_project_key=project.source_key,
                source_project_name=project.name,
                name=task_name,
                planned_start=planned_start,
                planned_end=planned_end,
                cost=to_float(row.get("Valor previsto"), 0.0),
                status=map_task_status_2025(row.get("PERCENTUAL REALIZADO"), actual_seconds),
                actual_seconds=actual_seconds,
                actual_start=actual_start,
            )
        )

    return ReplacementRecords(
        projects=projects,
        tasks=tasks,
        skipped_projects=skipped_projects,
        skipped_tasks=skipped_tasks,
    )


def year_bounds(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1), datetime(year + 1, 1, 1)


class SupabaseReplacementWriter:
    def __init__(self, database_url: str):
        import psycopg2

        self.conn = psycopg2.connect(database_url, connect_timeout=10)

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def count_existing(self, user_id: str, year: int) -> dict[str, int]:
        start, end = year_bounds(year)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select count(*)
                from projects
                where user_id = %s
                  and planned_start >= %s
                  and planned_start < %s
                """,
                (user_id, start, end),
            )
            projects = int(cur.fetchone()[0])

            cur.execute(
                """
                select count(*)
                from tasks t
                join projects p on p.id = t.project_id
                where p.user_id = %s
                  and p.planned_start >= %s
                  and p.planned_start < %s
                """,
                (user_id, start, end),
            )
            tasks = int(cur.fetchone()[0])

            cur.execute(
                """
                select count(*)
                from time_entries te
                join tasks t on t.id = te.task_id
                join projects p on p.id = t.project_id
                where p.user_id = %s
                  and p.planned_start >= %s
                  and p.planned_start < %s
                """,
                (user_id, start, end),
            )
            time_entries = int(cur.fetchone()[0])

        return {
            "projects": projects,
            "tasks": tasks,
            "time_entries": time_entries,
        }

    def delete_existing(self, user_id: str, year: int) -> dict[str, int]:
        start, end = year_bounds(year)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                delete from time_entries te
                using tasks t, projects p
                where te.task_id = t.id
                  and t.project_id = p.id
                  and p.user_id = %s
                  and p.planned_start >= %s
                  and p.planned_start < %s
                """,
                (user_id, start, end),
            )
            time_entries = int(cur.rowcount)

            cur.execute(
                """
                delete from tasks t
                using projects p
                where t.project_id = p.id
                  and p.user_id = %s
                  and p.planned_start >= %s
                  and p.planned_start < %s
                """,
                (user_id, start, end),
            )
            tasks = int(cur.rowcount)

            cur.execute(
                """
                delete from projects
                where user_id = %s
                  and planned_start >= %s
                  and planned_start < %s
                """,
                (user_id, start, end),
            )
            projects = int(cur.rowcount)

        return {
            "projects": projects,
            "tasks": tasks,
            "time_entries": time_entries,
        }

    def insert_project(self, user_id: str, project: Project2025Record) -> int:
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

    def insert_task(self, user_id: str, project_id: int, task: Task2025Record) -> int:
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

    def insert_time_entry(self, task_id: int, task: Task2025Record) -> int:
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


def time_entries_ready(records: ReplacementRecords) -> int:
    return sum(
        1
        for task in records.tasks
        if task.actual_seconds > 0 and task.actual_start is not None
    )


def build_initial_report(args: argparse.Namespace, records: ReplacementRecords) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "commit" if args.commit else "dry-run",
        "workbook": str(args.workbook),
        "year": args.year,
        "user_id": args.user_id,
        "counts": {
            "projects_ready": len(records.projects),
            "tasks_ready": len(records.tasks),
            "time_entries_ready": time_entries_ready(records),
            "projects_skipped": len(records.skipped_projects),
            "tasks_skipped": len(records.skipped_tasks),
            "delete_candidates_checked": False,
            "projects_would_delete": 0,
            "tasks_would_delete": 0,
            "time_entries_would_delete": 0,
            "projects_deleted": 0,
            "tasks_deleted": 0,
            "time_entries_deleted": 0,
            "projects_would_insert": len(records.projects),
            "tasks_would_insert": len(records.tasks),
            "time_entries_would_insert": time_entries_ready(records),
            "projects_inserted": 0,
            "tasks_inserted": 0,
            "time_entries_inserted": 0,
        },
        "skipped_projects": records.skipped_projects,
        "skipped_tasks": records.skipped_tasks,
    }


def update_delete_counts(
    counts: dict[str, Any],
    existing: dict[str, int],
    *,
    mode: str,
) -> None:
    if mode == "dry-run":
        counts["delete_candidates_checked"] = True
        counts["projects_would_delete"] = existing["projects"]
        counts["tasks_would_delete"] = existing["tasks"]
        counts["time_entries_would_delete"] = existing["time_entries"]
        return

    counts["projects_deleted"] = existing["projects"]
    counts["tasks_deleted"] = existing["tasks"]
    counts["time_entries_deleted"] = existing["time_entries"]


def run_replacement(
    args: argparse.Namespace,
    *,
    writer_cls: type[SupabaseReplacementWriter] = SupabaseReplacementWriter,
) -> dict[str, Any]:
    records = read_excel_records_2025(args.workbook, args.year)
    report = build_initial_report(args, records)
    counts = report["counts"]

    database_url = os.getenv("DATABASE_URL")
    if not args.commit:
        if database_url:
            writer = None
            try:
                writer = writer_cls(database_url)
                update_delete_counts(
                    counts,
                    writer.count_existing(args.user_id, args.year),
                    mode="dry-run",
                )
            except Exception as exc:
                report["delete_candidate_error"] = str(exc)
            finally:
                if writer is not None:
                    writer.close()
        write_json(args.report, report)
        return report

    if not database_url:
        raise MigrationError("DATABASE_URL nao definida. Configure no .env ou no ambiente.")
    if not records.projects:
        raise MigrationError("Nenhum projeto valido encontrado para substituir.")

    writer = writer_cls(database_url)
    project_db_ids: dict[str, int] = {}
    try:
        update_delete_counts(
            counts,
            writer.delete_existing(args.user_id, args.year),
            mode="commit",
        )

        for project in records.projects:
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
                        "reason": "project_id_not_available_after_project_import",
                    }
                )
                continue

            task_id = writer.insert_task(args.user_id, project_id, task)
            counts["tasks_inserted"] += 1

            if task.actual_seconds <= 0 or task.actual_start is None:
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
        description="Substitui PROJETOS_2025 e TAREFAS_2025 da A3 no Supabase."
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
        default=2025,
        help="Ano de planned_start que sera substituido. Padrao: 2025.",
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
        help="Apaga e grava no Supabase. Sem esta flag, executa apenas dry-run.",
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
        report = run_replacement(args)
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
        if counts["delete_candidates_checked"]:
            print(f"Projetos que seriam apagados: {counts['projects_would_delete']}")
            print(f"Tarefas que seriam apagadas: {counts['tasks_would_delete']}")
            print(f"Time entries que seriam apagados: {counts['time_entries_would_delete']}")
        elif report.get("delete_candidate_error"):
            print("Candidatos a exclusao nao conferidos; veja o relatorio.")
    else:
        print(f"Projetos apagados: {counts['projects_deleted']}")
        print(f"Tarefas apagadas: {counts['tasks_deleted']}")
        print(f"Time entries apagados: {counts['time_entries_deleted']}")
        print(f"Projetos inseridos: {counts['projects_inserted']}")
        print(f"Tarefas inseridas: {counts['tasks_inserted']}")
        print(f"Time entries inseridos: {counts['time_entries_inserted']}")
    print(f"Relatorio: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
