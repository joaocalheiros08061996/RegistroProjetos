#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Importa dados historicos da planilha A3 para o Supabase/Postgres.

Uso seguro padrao, sem escrita no banco:
    python automacoes/importar_a3_supabase.py --user-id <supabase-user-id>

Importacao real:
    python automacoes/importar_a3_supabase.py --user-id <supabase-user-id> --commit
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from domain.responsible import normalize_responsible_name

try:
    from automacoes.file_validation import validate_input_file, validate_optional_input_file
except ModuleNotFoundError:  # Execucao direta: python automacoes/importar_a3_supabase.py
    from file_validation import validate_input_file, validate_optional_input_file

DEFAULT_WORKBOOK = ROOT_DIR / "A3 - Gerenciamento de Projetos.xlsx"
DEFAULT_MANIFEST = Path(__file__).with_name("import_a3_manifest.json")
DEFAULT_REPORT = Path(__file__).with_name("import_a3_report.json")
EXCEL_ORIGIN = datetime(1899, 12, 30)
SECONDS_PER_DAY = 86400

INVALID_TEXT_VALUES = {
    "",
    "nan",
    "none",
    "null",
    "nao",
    "não",
    "#value!",
    "#valor!",
    "em andamento",
}

PROJECT_TYPE_MAP = {
    "layout": "LAYOUT",
    "exportacao": "EXPORTACAO",
    "exportacao de produtos": "EXPORTACAO",
    "normatizacao": "NORMATIZACAO",
    "normatizacao de processos": "NORMATIZACAO",
    "padronizacao": "PADRONIZACAO",
    "try out": "TRY_OUT",
    "try_out": "TRY_OUT",
    "mapeamento": "MAPEAMENTO",
    "mapeamento de processos": "MAPEAMENTO",
    "pecas": "PECAS",
    "pecas em geral": "PECAS",
}
LEGACY_PROJECT_TYPES = {"MELHORIA", "MELHORIA_PROC_NOVOS"}
LEGACY_PROJECT_TYPE_KEYS = {
    "melhoria",
    "melhoria continua dos processos",
    "melhoria de proc existentes",
    "melhoria de processos existentes",
    "melhoria proc novos",
    "melhoria de proc novos",
    "melhoria de processos novos",
}

SEVERITY_LABELS = {
    "sem gravidade": "Sem gravidade",
    "pouco grave": "Pouco grave",
    "grave": "Grave",
    "muito grave": "Muito grave",
    "gravissimo": "Gravíssimo",
}
SEVERITY_BY_NUMBER = {
    1: "Sem gravidade",
    2: "Pouco grave",
    3: "Grave",
    4: "Muito grave",
    5: "Gravíssimo",
}

URGENCY_LABELS = {
    "pode esperar": "Pode esperar",
    "pouco urgente": "Pouco urgente",
    "urgente": "Urgente",
    "mais rapido possivel": "Mais rápido possível",
    "imediatamente": "Imediatamente",
}
URGENCY_BY_NUMBER = {
    1: "Pode esperar",
    2: "Pouco urgente",
    3: "Urgente",
    4: "Mais rápido possível",
    5: "Imediatamente",
}

TREND_LABELS = {
    "nao tende a piorar": "Não tende a piorar",
    "piora em longo prazo": "Piora em longo prazo",
    "piora em medio prazo": "Piora em médio prazo",
    "piora em curto prazo": "Piora em curto prazo",
    "piora rapidamente": "Piora rapidamente",
}
TREND_BY_NUMBER = {
    1: "Não tende a piorar",
    2: "Piora em longo prazo",
    3: "Piora em médio prazo",
    4: "Piora em curto prazo",
    5: "Piora rapidamente",
}

OBJECTIVE_LABELS = {
    "objetivo totalmente definido": "Objetivo totalmente definido",
    "objetivo claro com pequenas ambiguidades": "Objetivo claro com pequenas ambiguidades",
    "objetivo parcialmente definido": "Objetivo parcialmente definido",
    "objetivo pouco claro": "Objetivo pouco claro",
    "objetivo indefinido ou exploratorio": "Objetivo indefinido ou exploratório",
}
OBJECTIVE_BY_NUMBER = {
    1: "Objetivo totalmente definido",
    2: "Objetivo claro com pequenas ambiguidades",
    3: "Objetivo parcialmente definido",
    4: "Objetivo pouco claro",
    5: "Objetivo indefinido ou exploratório",
}

METHOD_LABELS = {
    "metodos totalmente definidos e dominados": "Métodos totalmente definidos e dominados",
    "metodos conhecidos com pequenas adaptacoes": "Métodos conhecidos com pequenas adaptações",
    "metodos parcialmente conhecidos": "Métodos parcialmente conhecidos",
    "metodos pouco definidos": "Métodos pouco definidos",
    "metodos desconhecidos ou inexistentes": "Métodos desconhecidos ou inexistentes",
}
METHOD_BY_NUMBER = {
    1: "Métodos totalmente definidos e dominados",
    2: "Métodos conhecidos com pequenas adaptações",
    3: "Métodos parcialmente conhecidos",
    4: "Métodos pouco definidos",
    5: "Métodos desconhecidos ou inexistentes",
}


@dataclass(frozen=True)
class ProjectRecord:
    source_id: str
    name: str
    project_type: str
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
class TaskRecord:
    source_id: str
    source_project_id: str
    name: str
    planned_start: datetime
    planned_end: datetime
    cost: float
    status: str
    actual_seconds: int
    actual_start: datetime | None


@dataclass(frozen=True)
class WorkbookRecords:
    projects: list[ProjectRecord]
    tasks: list[TaskRecord]
    skipped_projects: list[dict[str, Any]]
    skipped_tasks: list[dict[str, Any]]


class MigrationError(RuntimeError):
    """Erro esperado de migracao com mensagem amigavel."""


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT_DIR / ".env")


def normalize_spaces(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text)


def normalize_key(value: Any) -> str:
    text = normalize_spaces(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_numbered_label(value: Any) -> str:
    text = normalize_spaces(value)
    return re.sub(r"^\s*\d+\s*[-.]\s*", "", text).strip()


def extract_leading_number(value: Any) -> int | None:
    match = re.match(r"^\s*(\d+)", normalize_spaces(value))
    if not match:
        return None
    return int(match.group(1))


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        return normalize_key(value) in INVALID_TEXT_VALUES
    return False


def to_text(value: Any) -> str:
    if is_missing(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return normalize_spaces(value)


def to_decimal(value: Any) -> Decimal | None:
    if is_missing(value):
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return Decimal(str(value))

    text = normalize_spaces(value)
    if not text:
        return None
    text = text.replace("R$", "").replace("%", "").strip()
    text = re.sub(r"[^0-9,.-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def to_float(value: Any, default: float = 0.0) -> float:
    numeric = to_decimal(value)
    if numeric is None:
        return default
    return float(numeric)


def to_positive_float(value: Any, default: float = 1.0) -> float:
    number = to_float(value, default)
    return number if number > 0 else default


def days_to_seconds(days: Any) -> int:
    numeric = to_decimal(days)
    if numeric is None or numeric <= 0:
        return 0
    return int(round(float(numeric) * SECONDS_PER_DAY))


def parse_excel_datetime(value: Any) -> datetime | None:
    if is_missing(value):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, time.min)

    numeric = to_decimal(value)
    if numeric is not None:
        serial = float(numeric)
        if serial <= 0:
            return None
        return EXCEL_ORIGIN + timedelta(days=serial)

    text = normalize_spaces(value)
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def map_project_type(value: Any) -> str:
    raw_key = normalize_key(strip_numbered_label(value))
    if raw_key in LEGACY_PROJECT_TYPE_KEYS:
        raise MigrationError(f"Tipo de projeto legado nao permitido: {value!r}")

    if raw_key in PROJECT_TYPE_MAP:
        return PROJECT_TYPE_MAP[raw_key]
    enum_key = normalize_spaces(value).strip().upper().replace(" ", "_")
    if enum_key in LEGACY_PROJECT_TYPES:
        raise MigrationError(f"Tipo de projeto legado nao permitido: {value!r}")

    if enum_key in set(PROJECT_TYPE_MAP.values()):
        return enum_key
    raise MigrationError(f"Tipo de projeto nao mapeado: {value!r}")


def map_numbered_enum(
    value: Any,
    labels: dict[str, str],
    numbers: dict[int, str],
    default: str,
) -> str:
    if is_missing(value):
        return default
    number = extract_leading_number(value)
    label_key = normalize_key(strip_numbered_label(value))
    if label_key in labels:
        return labels[label_key]
    if number in numbers:
        return numbers[number]
    raw_key = normalize_key(value)
    if raw_key in labels:
        return labels[raw_key]
    return default


def map_severity(value: Any) -> str:
    return map_numbered_enum(value, SEVERITY_LABELS, SEVERITY_BY_NUMBER, "Sem gravidade")


def map_urgency(value: Any) -> str:
    return map_numbered_enum(value, URGENCY_LABELS, URGENCY_BY_NUMBER, "Pode esperar")


def map_trend(value: Any) -> str:
    return map_numbered_enum(value, TREND_LABELS, TREND_BY_NUMBER, "Não tende a piorar")


def map_objective(value: Any) -> str:
    return map_numbered_enum(
        value,
        OBJECTIVE_LABELS,
        OBJECTIVE_BY_NUMBER,
        "Objetivo parcialmente definido",
    )


def map_method(value: Any) -> str:
    return map_numbered_enum(
        value,
        METHOD_LABELS,
        METHOD_BY_NUMBER,
        "Métodos parcialmente conhecidos",
    )


def map_task_status(value: Any, actual_seconds: int, percent_done: Any = None) -> str:
    status_key = normalize_key(value)
    percent = to_decimal(percent_done)
    if status_key == "concluido" or (percent is not None and percent >= 1):
        return "COMPLETED"
    if status_key in {"nao iniciado", "nao iniciada"}:
        return "PLANNED"
    if status_key in {"atrasado", "em andamento", "pausado"}:
        return "PAUSED" if actual_seconds > 0 else "PLANNED"
    return "PAUSED" if actual_seconds > 0 else "PLANNED"


def source_project_id_from_task_code(value: Any) -> str | None:
    text = to_text(value)
    match = re.match(r"^(\d+)", text)
    return match.group(1) if match else None


def normalize_source_id(value: Any) -> str | None:
    numeric = to_decimal(value)
    if numeric is None:
        return None
    if numeric != numeric.to_integral_value():
        return None
    return str(int(numeric))


def read_excel_records(workbook_path: Path) -> WorkbookRecords:
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

    def read_sheet(sheet_name: str, header_row: int) -> list[dict[str, Any]]:
        try:
            frame = pd.read_excel(
                workbook_path,
                sheet_name=sheet_name,
                header=header_row - 1,
                engine="openpyxl",
            )
        except ImportError as exc:
            raise MigrationError(
                "Dependencia ausente: instale openpyxl com `pip install -r requirements.txt`."
            ) from exc
        columns = [normalize_spaces(col) for col in frame.columns]
        records: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            record: dict[str, Any] = {}
            for column, value in zip(columns, row.tolist(), strict=False):
                record[column] = None if pd.isna(value) else value
            records.append(record)
        return records

    project_rows = read_sheet("PROJETOS", 4)
    task_rows = read_sheet("TAREFAS", 4)
    classified_rows = read_sheet("PROJETOS_CLASSIFICADOS", 1)
    return build_records(project_rows, task_rows, classified_rows)


def build_records(
    project_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    classified_rows: list[dict[str, Any]],
) -> WorkbookRecords:
    classified_by_name: dict[str, dict[str, Any]] = {}
    for row in classified_rows:
        name = to_text(row.get("PROJETOS"))
        if not name:
            continue
        classified_by_name.setdefault(normalize_key(name), row)

    projects: list[ProjectRecord] = []
    skipped_projects: list[dict[str, Any]] = []
    project_by_source_id: dict[str, ProjectRecord] = {}

    for row in project_rows:
        source_id = normalize_source_id(row.get("ID"))
        name = to_text(row.get("Projeto"))
        if not source_id or not name:
            continue

        classification = classified_by_name.get(normalize_key(name))
        if classification is None:
            skipped_projects.append(
                {"source_id": source_id, "name": name, "reason": "missing_classification"}
            )
            continue

        planned_start = parse_excel_datetime(row.get("Data Início Planej."))
        planned_end = parse_excel_datetime(row.get("Data Fim Planej."))
        if planned_start is None:
            planned_start = parse_excel_datetime(classification.get("DATA INÍCIO PLANEJ"))
        if planned_end is None:
            planned_end = parse_excel_datetime(classification.get("DATA FIM PLANEJ"))
        if planned_start is None or planned_end is None:
            skipped_projects.append(
                {"source_id": source_id, "name": name, "reason": "invalid_project_dates"}
            )
            continue
        if planned_end < planned_start:
            planned_end = planned_start

        try:
            project_type = map_project_type(classification.get("TIPO DE PROJETOS"))
        except MigrationError as exc:
            skipped_projects.append(
                {"source_id": source_id, "name": name, "reason": str(exc)}
            )
            continue

        project = ProjectRecord(
            source_id=source_id,
            name=name,
            project_type=project_type,
            responsible_login=normalize_responsible_name(
                to_text(row.get("Responsável"))
                or to_text(classification.get("RESPONSÁVEL"))
                or "nao_informado"
            ),
            fte=to_positive_float(row.get("FTEs"), to_positive_float(classification.get("FTes"), 1.0)),
            planned_start=planned_start,
            planned_end=planned_end,
            severity=map_severity(classification.get("GRAVIDADE")),
            urgency=map_urgency(classification.get("URGÊNCIA")),
            trend=map_trend(classification.get("TENDêNCIA")),
            objective=map_objective(classification.get("OBJETIVOS")),
            method=map_method(classification.get("MÉTODOS")),
            estimated_cost=to_float(row.get("Valor previsto"), 0.0),
        )
        projects.append(project)
        project_by_source_id[source_id] = project

    tasks: list[TaskRecord] = []
    skipped_tasks: list[dict[str, Any]] = []
    seen_task_ids: set[str] = set()

    for row in task_rows:
        source_id = to_text(row.get("Coluna1"))
        source_project_id = source_project_id_from_task_code(source_id)
        task_name = to_text(row.get("Tarefa"))
        project_name = to_text(row.get("Projeto"))
        if not source_id or not source_project_id or not task_name:
            continue
        if source_id in seen_task_ids:
            skipped_tasks.append(
                {
                    "source_id": source_id,
                    "project": project_name,
                    "name": task_name,
                    "reason": "duplicate_task_source_id",
                }
            )
            continue
        seen_task_ids.add(source_id)

        project = project_by_source_id.get(source_project_id)
        if project is None:
            skipped_tasks.append(
                {
                    "source_id": source_id,
                    "source_project_id": source_project_id,
                    "project": project_name,
                    "name": task_name,
                    "reason": "project_not_imported",
                }
            )
            continue

        planned_start = parse_excel_datetime(row.get("Data Início Planej.")) or project.planned_start
        planned_end = parse_excel_datetime(row.get("Data Fim Planej.")) or project.planned_end
        if planned_end < planned_start:
            planned_end = planned_start

        actual_seconds = days_to_seconds(row.get("Esforço Real"))
        status = map_task_status(row.get("Status"), actual_seconds, row.get("% Finalizado"))
        actual_start = None
        if actual_seconds > 0:
            actual_start = parse_excel_datetime(row.get("Data Início Real")) or planned_start

        tasks.append(
            TaskRecord(
                source_id=source_id,
                source_project_id=source_project_id,
                name=task_name,
                planned_start=planned_start,
                planned_end=planned_end,
                cost=to_float(row.get("Valor previsto"), 0.0),
                status=status,
                actual_seconds=actual_seconds,
                actual_start=actual_start,
            )
        )

    return WorkbookRecords(
        projects=projects,
        tasks=tasks,
        skipped_projects=skipped_projects,
        skipped_tasks=skipped_tasks,
    )


def empty_manifest(user_id: str | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "user_id": user_id,
        "projects": {},
        "tasks": {},
        "time_entries": {},
    }


def load_manifest(path: Path, user_id: str) -> dict[str, Any]:
    try:
        path = validate_optional_input_file(
            path,
            allowed_suffixes={".json"},
            description="Manifesto",
        )
    except (FileNotFoundError, ValueError) as exc:
        raise MigrationError(str(exc)) from exc
    if not path.exists():
        return empty_manifest(user_id)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise MigrationError(f"Manifesto invalido: {path}")
    data.setdefault("version", 1)
    data.setdefault("projects", {})
    data.setdefault("tasks", {})
    data.setdefault("time_entries", {})
    manifest_user_id = data.get("user_id")
    if manifest_user_id and manifest_user_id != user_id:
        raise MigrationError(
            "Manifesto pertence a outro user_id. Use outro caminho em --manifest "
            "ou revise o arquivo antes de continuar."
        )
    data["user_id"] = user_id
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    tmp_path.replace(path)


class SupabaseWriter:
    def __init__(self, database_url: str):
        import psycopg2

        self.conn = psycopg2.connect(database_url)

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def project_exists(self, project_id: int, user_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "select 1 from projects where id = %s and user_id = %s",
                (project_id, user_id),
            )
            return cur.fetchone() is not None

    def task_exists(self, task_id: int, project_id: int, user_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "select 1 from tasks where id = %s and project_id = %s and user_id = %s",
                (task_id, project_id, user_id),
            )
            return cur.fetchone() is not None

    def time_entry_exists(self, entry_id: int, task_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "select 1 from time_entries where id = %s and task_id = %s",
                (entry_id, task_id),
            )
            return cur.fetchone() is not None

    def insert_project(self, user_id: str, project: ProjectRecord) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into projects (
                    user_id, name, project_type, responsible_login, fte,
                    planned_start, planned_end, severity, urgency, trend,
                    objective, method, estimated_cost
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                returning id
                """,
                (
                    user_id,
                    project.name,
                    project.project_type,
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

    def insert_task(self, user_id: str, project_id: int, task: TaskRecord) -> int:
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

    def insert_time_entry(self, task_id: int, task: TaskRecord) -> int:
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


def manifest_id(entry: dict[str, Any] | None) -> int | None:
    if not entry:
        return None
    raw_id = entry.get("supabase_id")
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


def build_initial_report(args: argparse.Namespace, records: WorkbookRecords) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "commit" if args.commit else "dry-run",
        "workbook": str(args.workbook),
        "manifest": str(args.manifest),
        "user_id": args.user_id,
        "counts": {
            "projects_ready": len(records.projects),
            "tasks_ready": len(records.tasks),
            "projects_skipped": len(records.skipped_projects),
            "tasks_skipped": len(records.skipped_tasks),
            "projects_inserted": 0,
            "projects_existing_from_manifest": 0,
            "tasks_inserted": 0,
            "tasks_existing_from_manifest": 0,
            "time_entries_inserted": 0,
            "time_entries_existing_from_manifest": 0,
            "projects_would_insert": 0,
            "tasks_would_insert": 0,
            "time_entries_would_insert": 0,
        },
        "skipped_projects": records.skipped_projects,
        "skipped_tasks": records.skipped_tasks[:200],
    }


def run_import(args: argparse.Namespace) -> dict[str, Any]:
    records = read_excel_records(args.workbook)
    manifest = load_manifest(args.manifest, args.user_id)
    report = build_initial_report(args, records)
    counts = report["counts"]

    project_db_ids: dict[str, int] = {}
    task_db_ids: dict[str, int] = {}

    if not args.commit:
        for project in records.projects:
            project_entry = manifest["projects"].get(project.source_id)
            if manifest_id(project_entry):
                counts["projects_existing_from_manifest"] += 1
            else:
                counts["projects_would_insert"] += 1
        for task in records.tasks:
            task_entry = manifest["tasks"].get(task.source_id)
            time_entry = manifest["time_entries"].get(task.source_id)
            if manifest_id(task_entry):
                counts["tasks_existing_from_manifest"] += 1
            else:
                counts["tasks_would_insert"] += 1
            if task.actual_seconds > 0:
                if manifest_id(time_entry):
                    counts["time_entries_existing_from_manifest"] += 1
                else:
                    counts["time_entries_would_insert"] += 1
        write_json(args.report, report)
        return report

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise MigrationError("DATABASE_URL nao definida. Configure no .env ou no ambiente.")

    writer = SupabaseWriter(database_url)
    try:
        for project in records.projects:
            project_entry = manifest["projects"].get(project.source_id)
            project_id = manifest_id(project_entry)
            if project_id and writer.project_exists(project_id, args.user_id):
                project_db_ids[project.source_id] = project_id
                counts["projects_existing_from_manifest"] += 1
                continue

            project_id = writer.insert_project(args.user_id, project)
            project_db_ids[project.source_id] = project_id
            manifest["projects"][project.source_id] = {
                "supabase_id": project_id,
                "name": project.name,
                "project_type": project.project_type,
            }
            counts["projects_inserted"] += 1

        for task in records.tasks:
            project_id = project_db_ids.get(task.source_project_id)
            if project_id is None:
                report.setdefault("runtime_skipped_tasks", []).append(
                    {
                        "source_id": task.source_id,
                        "name": task.name,
                        "reason": "project_id_not_available_after_project_import",
                    }
                )
                continue

            task_entry = manifest["tasks"].get(task.source_id)
            task_id = manifest_id(task_entry)
            if task_id and writer.task_exists(task_id, project_id, args.user_id):
                task_db_ids[task.source_id] = task_id
                counts["tasks_existing_from_manifest"] += 1
            else:
                task_id = writer.insert_task(args.user_id, project_id, task)
                task_db_ids[task.source_id] = task_id
                manifest["tasks"][task.source_id] = {
                    "supabase_id": task_id,
                    "project_source_id": task.source_project_id,
                    "project_supabase_id": project_id,
                    "name": task.name,
                    "status": task.status,
                }
                counts["tasks_inserted"] += 1

            if task.actual_seconds <= 0:
                continue

            entry = manifest["time_entries"].get(task.source_id)
            entry_id = manifest_id(entry)
            if entry_id and writer.time_entry_exists(entry_id, task_id):
                counts["time_entries_existing_from_manifest"] += 1
                continue

            entry_id = writer.insert_time_entry(task_id, task)
            manifest["time_entries"][task.source_id] = {
                "supabase_id": entry_id,
                "task_source_id": task.source_id,
                "task_supabase_id": task_id,
                "actual_seconds": task.actual_seconds,
                "start_time": task.actual_start.isoformat() if task.actual_start else None,
            }
            counts["time_entries_inserted"] += 1

        writer.commit()
    except Exception:
        writer.rollback()
        raise
    finally:
        writer.close()

    write_json(args.manifest, manifest)
    write_json(args.report, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa PROJETOS, TAREFAS e PROJETOS_CLASSIFICADOS da A3 para Supabase."
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_WORKBOOK,
        help=f"Caminho da planilha .xlsx. Padrao: {DEFAULT_WORKBOOK}",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Manifesto idempotente. Padrao: {DEFAULT_MANIFEST}",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Relatorio JSON de execucao. Padrao: {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("SUPABASE_USER_ID"),
        help="User ID do Supabase. Tambem pode vir de SUPABASE_USER_ID.",
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
    args.manifest = args.manifest.resolve()
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
    print(f"Projetos prontos: {counts['projects_ready']}")
    print(f"Tarefas prontas: {counts['tasks_ready']}")
    print(f"Projetos pulados: {counts['projects_skipped']}")
    print(f"Tarefas puladas: {counts['tasks_skipped']}")
    if report["mode"] == "dry-run":
        print(f"Projetos que seriam inseridos: {counts['projects_would_insert']}")
        print(f"Tarefas que seriam inseridas: {counts['tasks_would_insert']}")
        print(f"Time entries que seriam inseridos: {counts['time_entries_would_insert']}")
    else:
        print(f"Projetos inseridos: {counts['projects_inserted']}")
        print(f"Tarefas inseridas: {counts['tasks_inserted']}")
        print(f"Time entries inseridos: {counts['time_entries_inserted']}")
    print(f"Relatorio: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
