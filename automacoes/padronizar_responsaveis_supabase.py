#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Padroniza responsaveis historicos em projects e atividades.

Dry-run seguro:
    python automacoes/padronizar_responsaveis_supabase.py

Atualizacao real:
    python automacoes/padronizar_responsaveis_supabase.py --commit
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from domain.responsible import (  # noqa: E402
    is_uuid_text,
    normalize_responsible_name,
    normalize_responsible_spaces,
)

DEFAULT_REPORT = Path("/tmp/padronizar_responsaveis_supabase_report.json")
SAMPLE_LIMIT = 25


class ResponsibleNormalizationError(RuntimeError):
    """Erro esperado da normalizacao de responsaveis."""


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    tmp_path.replace(path)


class SupabaseResponsibleNormalizer:
    def __init__(self, database_url: str):
        import psycopg2
        from psycopg2.extras import RealDictCursor

        self._cursor_factory = RealDictCursor
        self.conn = psycopg2.connect(database_url, connect_timeout=10)

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def fetch_projects(self) -> list[dict[str, Any]]:
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(
                """
                select id, responsible_login
                from projects
                order by id
                """
            )
            return [dict(row) for row in (cur.fetchall() or [])]

    def fetch_activities(self) -> list[dict[str, Any]]:
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(
                """
                select id, user_id, responsavel
                from atividades
                order by id
                """
            )
            return [dict(row) for row in (cur.fetchall() or [])]

    def update_project_responsible(self, project_id: int, responsible_login: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update projects
                set responsible_login = %s
                where id = %s
                """,
                (responsible_login, project_id),
            )

    def update_activity_responsible(
        self,
        activity_id: int,
        user_id: str,
        responsavel: str | None,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update atividades
                set user_id = %s,
                    responsavel = %s
                where id = %s
                """,
                (user_id, responsavel, activity_id),
            )


def project_change(row: dict[str, Any]) -> dict[str, Any] | None:
    current = normalize_responsible_spaces(row.get("responsible_login"))
    normalized = normalize_responsible_name(current)
    if not normalized or normalized == current:
        return None
    return {
        "id": int(row["id"]),
        "responsible_login_before": current,
        "responsible_login_after": normalized,
    }


def activity_change(row: dict[str, Any]) -> dict[str, Any] | None:
    current_user_id = normalize_responsible_spaces(row.get("user_id"))
    current_responsavel = row.get("responsavel")
    current_responsavel_text = (
        normalize_responsible_spaces(current_responsavel)
        if current_responsavel is not None
        else None
    )

    if current_user_id and not is_uuid_text(current_user_id):
        normalized_user_id = normalize_responsible_name(current_user_id)
        normalized_responsavel = normalized_user_id
    else:
        normalized_user_id = current_user_id
        normalized_responsavel = (
            normalize_responsible_name(current_responsavel_text)
            if current_responsavel_text
            else current_responsavel_text
        )

    user_changed = normalized_user_id != current_user_id
    responsavel_changed = normalized_responsavel != current_responsavel_text
    if not user_changed and not responsavel_changed:
        return None

    return {
        "id": int(row["id"]),
        "user_id_before": current_user_id,
        "user_id_after": normalized_user_id,
        "responsavel_before": current_responsavel_text,
        "responsavel_after": normalized_responsavel,
        "user_id_changed": user_changed,
        "responsavel_changed": responsavel_changed,
    }


def build_report(
    *,
    mode: str,
    project_rows: list[dict[str, Any]],
    activity_rows: list[dict[str, Any]],
    project_updates: list[dict[str, Any]],
    activity_updates: list[dict[str, Any]],
) -> dict[str, Any]:
    activity_user_updates = sum(1 for item in activity_updates if item["user_id_changed"])
    activity_responsavel_updates = sum(
        1 for item in activity_updates if item["responsavel_changed"]
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "counts": {
            "projects_scanned": len(project_rows),
            "projects_would_update": len(project_updates),
            "projects_updated": 0,
            "activities_scanned": len(activity_rows),
            "activities_rows_would_update": len(activity_updates),
            "activities_rows_updated": 0,
            "activities_user_id_would_update": activity_user_updates,
            "activities_user_id_updated": 0,
            "activities_responsavel_would_update": activity_responsavel_updates,
            "activities_responsavel_updated": 0,
        },
        "samples": {
            "projects": project_updates[:SAMPLE_LIMIT],
            "activities": activity_updates[:SAMPLE_LIMIT],
        },
    }


def run_normalization(
    args: argparse.Namespace,
    *,
    writer_cls: type[SupabaseResponsibleNormalizer] = SupabaseResponsibleNormalizer,
) -> dict[str, Any]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ResponsibleNormalizationError(
            "DATABASE_URL nao definida. Configure no .env ou no ambiente."
        )

    writer = writer_cls(database_url)
    try:
        project_rows = writer.fetch_projects()
        activity_rows = writer.fetch_activities()
        project_updates = [
            change for row in project_rows if (change := project_change(row)) is not None
        ]
        activity_updates = [
            change for row in activity_rows if (change := activity_change(row)) is not None
        ]
        report = build_report(
            mode="commit" if args.commit else "dry-run",
            project_rows=project_rows,
            activity_rows=activity_rows,
            project_updates=project_updates,
            activity_updates=activity_updates,
        )

        if args.commit:
            for item in project_updates:
                writer.update_project_responsible(
                    item["id"],
                    item["responsible_login_after"],
                )
            for item in activity_updates:
                writer.update_activity_responsible(
                    item["id"],
                    item["user_id_after"],
                    item["responsavel_after"],
                )
            writer.commit()

            counts = report["counts"]
            counts["projects_updated"] = len(project_updates)
            counts["activities_rows_updated"] = len(activity_updates)
            counts["activities_user_id_updated"] = counts[
                "activities_user_id_would_update"
            ]
            counts["activities_responsavel_updated"] = counts[
                "activities_responsavel_would_update"
            ]
    except Exception:
        if args.commit:
            writer.rollback()
        raise
    finally:
        writer.close()

    write_json(args.report, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Padroniza nomes de responsaveis em projects e atividades."
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Relatorio JSON. Padrao: {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Atualiza o Supabase. Sem esta flag, executa apenas dry-run.",
    )
    args = parser.parse_args(argv)
    args.report = args.report.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv_if_available()
    args = parse_args(argv)
    try:
        report = run_normalization(args)
    except ResponsibleNormalizationError as exc:
        print(f"Erro de normalizacao: {exc}")
        return 2
    except Exception as exc:  # pragma: no cover - mantem stack curta para uso manual.
        print(f"Erro inesperado: {exc}")
        return 1

    counts = report["counts"]
    print(f"Modo: {report['mode']}")
    print(f"Projetos lidos: {counts['projects_scanned']}")
    print(f"Projetos a padronizar: {counts['projects_would_update']}")
    print(f"Atividades lidas: {counts['activities_scanned']}")
    print(f"Atividades a padronizar: {counts['activities_rows_would_update']}")
    if report["mode"] == "commit":
        print(f"Projetos atualizados: {counts['projects_updated']}")
        print(f"Atividades atualizadas: {counts['activities_rows_updated']}")
    print(f"Relatorio: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
