#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Importa o CSV historico de atividades para public.atividades.

Dry-run seguro:
    python automacoes/importar_atividades_supabase.py

Importacao real:
    python automacoes/importar_atividades_supabase.py --commit
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT_DIR / "atividades_rows (21).csv"
DEFAULT_USER_MAP = Path(__file__).with_name("atividades_user_map.json")
DEFAULT_MANIFEST = Path(__file__).with_name("import_atividades_manifest.json")
DEFAULT_REPORT = Path(__file__).with_name("import_atividades_report.json")
SOURCE_TIMEZONE = ZoneInfo("America/Sao_Paulo")
REQUIRED_COLUMNS = {
    "id",
    "tipo_atividade",
    "descricao",
    "inicio",
    "fim",
    "user_id",
    "ano",
    "mes",
    "dia",
    "horas_trabalhadas",
}


class ActivityImportError(RuntimeError):
    """Erro esperado de importacao de atividades."""


@dataclass(frozen=True)
class UserMapping:
    source_label: str
    user_id: str
    responsavel: str


@dataclass(frozen=True)
class ActivityRecord:
    source_id: str
    source_user_label: str
    user_id: str
    responsavel: str
    tipo_atividade: str
    descricao: str
    inicio: datetime
    fim: datetime
    ano: int
    mes: int
    dia: int
    horas_trabalhadas: Decimal


@dataclass(frozen=True)
class ParsedActivities:
    records: list[ActivityRecord]
    skipped: list[dict[str, Any]]
    source_rows: int


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
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ").strip())


def normalize_key(value: Any) -> str:
    text = normalize_spaces(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_decimal(value: Any) -> Decimal | None:
    text = normalize_spaces(value)
    if not text:
        return None
    text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_positive_hours(value: Any) -> Decimal | None:
    number = parse_decimal(value)
    if number is None or number < 0:
        return None
    return number


def parse_datetime(value: Any) -> datetime | None:
    text = normalize_spaces(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return parsed.replace(tzinfo=SOURCE_TIMEZONE)
    return parsed.astimezone(SOURCE_TIMEZONE)


def parse_int(value: Any) -> int | None:
    number = parse_decimal(value)
    if number is None or number != number.to_integral_value():
        return None
    return int(number)


def calculated_hours(started_at: datetime, finished_at: datetime) -> Decimal:
    seconds = Decimal(str((finished_at - started_at).total_seconds()))
    return (seconds / Decimal("3600")).quantize(Decimal("0.0000000001"))


def stable_natural_key(record: ActivityRecord) -> tuple[str, str, datetime, datetime, str]:
    return (
        record.user_id,
        record.tipo_atividade,
        record.inicio.astimezone(timezone.utc),
        record.fim.astimezone(timezone.utc),
        record.descricao,
    )


def read_csv_rows(csv_path: Path) -> list[dict[str, str | None]]:
    if not csv_path.exists():
        raise ActivityImportError(f"CSV nao encontrado: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.DictReader(handle, dialect=dialect)
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        if missing:
            raise ActivityImportError(f"CSV sem colunas obrigatorias: {', '.join(missing)}")
        return [dict(row) for row in reader]


def load_user_map(path: Path) -> dict[str, UserMapping]:
    if not path.exists():
        raise ActivityImportError(f"Mapa de usuarios nao encontrado: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    users = payload.get("users", payload)
    if not isinstance(users, dict):
        raise ActivityImportError("Mapa de usuarios invalido: esperado objeto JSON em `users`.")

    mappings: dict[str, UserMapping] = {}
    for source_label, raw_entry in users.items():
        if not isinstance(raw_entry, dict):
            continue
        user_id = normalize_spaces(raw_entry.get("user_id"))
        responsavel = (
            normalize_spaces(raw_entry.get("responsavel"))
            or normalize_spaces(raw_entry.get("user_email"))
            or normalize_spaces(source_label)
        )
        if not user_id:
            continue
        mapping = UserMapping(
            source_label=normalize_spaces(source_label),
            user_id=user_id,
            responsavel=responsavel,
        )
        mappings[normalize_key(source_label)] = mapping
    return mappings


def parse_activities(
    rows: list[dict[str, str | None]],
    user_map: dict[str, UserMapping],
) -> ParsedActivities:
    records: list[ActivityRecord] = []
    skipped: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        source_id = normalize_spaces(row.get("id"))
        activity_type = normalize_spaces(row.get("tipo_atividade"))
        descricao = normalize_spaces(row.get("descricao"))
        source_user = normalize_spaces(row.get("user_id"))
        started_at = parse_datetime(row.get("inicio"))
        finished_at = parse_datetime(row.get("fim"))

        def skip(reason: str, extra: dict[str, Any] | None = None) -> None:
            payload: dict[str, Any] = {
                "row_number": row_number,
                "source_id": source_id,
                "source_user": source_user,
                "tipo_atividade": activity_type,
                "reason": reason,
            }
            if extra:
                payload.update(extra)
            skipped.append(payload)

        if not source_id:
            skip("missing_source_id")
            continue
        if source_id in seen_source_ids:
            skip("duplicate_source_id")
            continue
        seen_source_ids.add(source_id)
        if not activity_type:
            skip("missing_activity_type")
            continue
        if not source_user:
            skip("missing_source_user")
            continue

        mapping = user_map.get(normalize_key(source_user))
        if mapping is None:
            skip("missing_user_mapping")
            continue
        if started_at is None:
            skip("invalid_start_datetime")
            continue
        if not normalize_spaces(row.get("fim")):
            skip("open_activity")
            continue
        if finished_at is None:
            skip("invalid_end_datetime")
            continue
        if finished_at < started_at:
            skip("end_before_start")
            continue

        ano = parse_int(row.get("ano")) or started_at.year
        mes = parse_int(row.get("mes")) or started_at.month
        dia = parse_int(row.get("dia")) or started_at.day
        if mes < 1 or mes > 12:
            mes = started_at.month
        if dia < 1 or dia > 31:
            dia = started_at.day

        hours = parse_positive_hours(row.get("horas_trabalhadas"))
        if hours is None:
            hours = calculated_hours(started_at, finished_at)

        records.append(
            ActivityRecord(
                source_id=source_id,
                source_user_label=source_user,
                user_id=mapping.user_id,
                responsavel=mapping.responsavel,
                tipo_atividade=activity_type,
                descricao=descricao,
                inicio=started_at,
                fim=finished_at,
                ano=ano,
                mes=mes,
                dia=dia,
                horas_trabalhadas=hours,
            )
        )

    return ParsedActivities(records=records, skipped=skipped, source_rows=len(rows))


def empty_manifest() -> dict[str, Any]:
    return {"version": 1, "activities": {}}


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_manifest()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ActivityImportError(f"Manifesto invalido: {path}")
    payload.setdefault("version", 1)
    payload.setdefault("activities", {})
    return payload


def manifest_id(entry: dict[str, Any] | None) -> int | None:
    if not entry:
        return None
    try:
        return int(entry.get("supabase_id"))
    except (TypeError, ValueError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    tmp_path.replace(path)


class ActivityWriter:
    def __init__(self, database_url: str):
        import psycopg2

        self.conn = psycopg2.connect(database_url)

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def activity_id_exists(self, activity_id: int) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("select 1 from atividades where id = %s", (activity_id,))
            return cur.fetchone() is not None

    def find_existing_by_natural_key(self, record: ActivityRecord) -> int | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select id
                from atividades
                where user_id = %s
                  and tipo_atividade = %s
                  and inicio = %s
                  and fim = %s
                  and coalesce(descricao, '') = %s
                limit 1
                """,
                (
                    record.user_id,
                    record.tipo_atividade,
                    record.inicio,
                    record.fim,
                    record.descricao,
                ),
            )
            row = cur.fetchone()
        return int(row[0]) if row else None

    def insert_activity(self, record: ActivityRecord) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into atividades (
                    user_id,
                    tipo_atividade,
                    responsavel,
                    descricao,
                    inicio,
                    fim,
                    ano,
                    mes,
                    dia,
                    horas_trabalhadas
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                returning id
                """,
                (
                    record.user_id,
                    record.tipo_atividade,
                    record.responsavel,
                    record.descricao,
                    record.inicio,
                    record.fim,
                    record.ano,
                    record.mes,
                    record.dia,
                    record.horas_trabalhadas,
                ),
            )
            return int(cur.fetchone()[0])


def build_report(args: argparse.Namespace, parsed: ParsedActivities) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "commit" if args.commit else "dry-run",
        "csv": str(args.csv),
        "user_map": str(args.user_map),
        "manifest": str(args.manifest),
        "counts": {
            "source_rows": parsed.source_rows,
            "activities_ready": len(parsed.records),
            "activities_skipped": len(parsed.skipped),
            "activities_inserted": 0,
            "activities_existing_from_manifest": 0,
            "activities_existing_by_natural_key": 0,
            "activities_would_insert": 0,
        },
        "skipped": parsed.skipped,
    }


def run_import(args: argparse.Namespace) -> dict[str, Any]:
    rows = read_csv_rows(args.csv)
    user_map = load_user_map(args.user_map)
    parsed = parse_activities(rows, user_map)
    manifest = load_manifest(args.manifest)
    report = build_report(args, parsed)
    counts = report["counts"]

    if not args.commit:
        for record in parsed.records:
            if manifest_id(manifest["activities"].get(record.source_id)):
                counts["activities_existing_from_manifest"] += 1
            else:
                counts["activities_would_insert"] += 1
        write_json(args.report, report)
        return report

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ActivityImportError("DATABASE_URL nao definida. Configure no .env ou no ambiente.")

    writer = ActivityWriter(database_url)
    try:
        for record in parsed.records:
            entry = manifest["activities"].get(record.source_id)
            existing_id = manifest_id(entry)
            if existing_id and writer.activity_id_exists(existing_id):
                counts["activities_existing_from_manifest"] += 1
                continue

            natural_id = writer.find_existing_by_natural_key(record)
            if natural_id is not None:
                manifest["activities"][record.source_id] = {
                    "supabase_id": natural_id,
                    "source_user": record.source_user_label,
                    "user_id": record.user_id,
                    "tipo_atividade": record.tipo_atividade,
                }
                counts["activities_existing_by_natural_key"] += 1
                continue

            activity_id = writer.insert_activity(record)
            manifest["activities"][record.source_id] = {
                "supabase_id": activity_id,
                "source_user": record.source_user_label,
                "user_id": record.user_id,
                "tipo_atividade": record.tipo_atividade,
            }
            counts["activities_inserted"] += 1
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
    parser = argparse.ArgumentParser(description="Importa atividades historicas do CSV para Supabase.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help=f"CSV de entrada. Padrao: {DEFAULT_CSV}")
    parser.add_argument("--user-map", type=Path, default=DEFAULT_USER_MAP, help=f"Mapa nome -> UUID. Padrao: {DEFAULT_USER_MAP}")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help=f"Manifesto idempotente. Padrao: {DEFAULT_MANIFEST}")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help=f"Relatorio JSON. Padrao: {DEFAULT_REPORT}")
    parser.add_argument("--commit", action="store_true", help="Grava no banco. Sem esta flag, roda dry-run.")
    args = parser.parse_args(argv)
    args.csv = args.csv.resolve()
    args.user_map = args.user_map.resolve()
    args.manifest = args.manifest.resolve()
    args.report = args.report.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_available()
    args = parse_args(argv)
    try:
        report = run_import(args)
    except ActivityImportError as exc:
        print(f"Erro de importacao: {exc}")
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"Erro inesperado: {exc}")
        return 1

    counts = report["counts"]
    print(f"Modo: {report['mode']}")
    print(f"Linhas no CSV: {counts['source_rows']}")
    print(f"Atividades prontas: {counts['activities_ready']}")
    print(f"Atividades puladas: {counts['activities_skipped']}")
    if counts["activities_ready"] == 0 and counts["activities_skipped"] > 0:
        print(
            "Nenhuma atividade ficou pronta para importar. "
            "Preencha `automacoes/atividades_user_map.json` com os UUIDs "
            "Supabase em `user_id` e rode novamente."
        )
    if report["mode"] == "dry-run":
        print(f"Atividades que seriam inseridas: {counts['activities_would_insert']}")
    else:
        print(f"Atividades inseridas: {counts['activities_inserted']}")
        print(f"Atividades ja existentes via manifesto: {counts['activities_existing_from_manifest']}")
        print(f"Atividades ja existentes por chave natural: {counts['activities_existing_by_natural_key']}")
    print(f"Relatorio: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
