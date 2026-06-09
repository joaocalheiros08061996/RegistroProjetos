#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Associa projetos por nome a um user_id do Supabase.

Dry-run seguro:
    python automacoes/associar_projeto_usuario_supabase.py

Atualizacao real:
    python automacoes/associar_projeto_usuario_supabase.py --commit
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

from domain.responsible import is_uuid_text, normalize_responsible_spaces  # noqa: E402

DEFAULT_PROJECT_NAME = "Projeto de Normatização do Processo de Soldagem"
DEFAULT_USER_ID = "9dba7386-6ecb-4475-b969-31af32258b71"
DEFAULT_REPORT = Path("/tmp/associar_projeto_usuario_supabase_report.json")
SAMPLE_LIMIT = 25


class ProjectUserAssociationError(RuntimeError):
    """Erro esperado da associacao de projeto a usuario."""


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


class SupabaseProjectUserAssociator:
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

    def fetch_projects_by_name(self, project_name: str) -> list[dict[str, Any]]:
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(
                """
                select id, name, user_id, responsible_login
                from projects
                where name = %s
                order by id
                """,
                (project_name,),
            )
            return [dict(row) for row in (cur.fetchall() or [])]

    def fetch_task_owner_counts(self, project_ids: list[int]) -> list[dict[str, Any]]:
        if not project_ids:
            return []
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(
                """
                select project_id, user_id, count(*) as task_count
                from tasks
                where project_id = any(%s)
                group by project_id, user_id
                order by project_id, user_id
                """,
                (project_ids,),
            )
            return [dict(row) for row in (cur.fetchall() or [])]

    def fetch_task_name_conflicts(self, project_ids: list[int]) -> list[dict[str, Any]]:
        if not project_ids:
            return []
        with self.conn.cursor(cursor_factory=self._cursor_factory) as cur:
            cur.execute(
                """
                select
                    project_id,
                    name,
                    count(*) as task_count,
                    array_agg(id order by id) as task_ids,
                    array_agg(distinct user_id order by user_id) as user_ids
                from tasks
                where project_id = any(%s)
                group by project_id, name
                having count(*) > 1
                order by project_id, name
                """,
                (project_ids,),
            )
            return [dict(row) for row in (cur.fetchall() or [])]

    def update_projects_user(self, project_ids: list[int], user_id: str) -> int:
        if not project_ids:
            return 0
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update projects
                set user_id = %s
                where id = any(%s)
                  and user_id <> %s
                """,
                (user_id, project_ids, user_id),
            )
            return cur.rowcount

    def update_tasks_user(self, project_ids: list[int], user_id: str) -> int:
        if not project_ids:
            return 0
        with self.conn.cursor() as cur:
            cur.execute(
                """
                update tasks
                set user_id = %s
                where project_id = any(%s)
                  and user_id <> %s
                """,
                (user_id, project_ids, user_id),
            )
            return cur.rowcount


def build_report(
    *,
    mode: str,
    project_name: str,
    target_user_id: str,
    projects: list[dict[str, Any]],
    task_owner_counts: list[dict[str, Any]],
    task_conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    projects_would_update = sum(
        1 for project in projects if project.get("user_id") != target_user_id
    )
    tasks_scanned = sum(int(row["task_count"]) for row in task_owner_counts)
    tasks_would_update = sum(
        int(row["task_count"])
        for row in task_owner_counts
        if row.get("user_id") != target_user_id
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "project_name": project_name,
        "target_user_id": target_user_id,
        "can_commit": bool(projects) and not task_conflicts,
        "counts": {
            "projects_matched": len(projects),
            "projects_would_update": projects_would_update,
            "projects_updated": 0,
            "tasks_scanned": tasks_scanned,
            "tasks_would_update": tasks_would_update,
            "tasks_updated": 0,
            "task_conflicts": len(task_conflicts),
        },
        "samples": {
            "projects": projects[:SAMPLE_LIMIT],
            "task_owner_counts": task_owner_counts[:SAMPLE_LIMIT],
            "task_conflicts": task_conflicts[:SAMPLE_LIMIT],
        },
    }


def run_association(
    args: argparse.Namespace,
    *,
    writer_cls: type[SupabaseProjectUserAssociator] = SupabaseProjectUserAssociator,
) -> dict[str, Any]:
    project_name = normalize_responsible_spaces(args.project_name)
    target_user_id = normalize_responsible_spaces(args.user_id)
    if not project_name:
        raise ProjectUserAssociationError("Nome do projeto nao informado.")
    if not is_uuid_text(target_user_id):
        raise ProjectUserAssociationError("UID do usuario deve ser um UUID valido.")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ProjectUserAssociationError(
            "DATABASE_URL nao definida. Configure no .env ou no ambiente."
        )

    writer = writer_cls(database_url)
    try:
        projects = writer.fetch_projects_by_name(project_name)
        project_ids = [int(project["id"]) for project in projects]
        task_owner_counts = writer.fetch_task_owner_counts(project_ids)
        task_conflicts = writer.fetch_task_name_conflicts(project_ids)
        report = build_report(
            mode="commit" if args.commit else "dry-run",
            project_name=project_name,
            target_user_id=target_user_id,
            projects=projects,
            task_owner_counts=task_owner_counts,
            task_conflicts=task_conflicts,
        )

        if not projects:
            write_json(args.report, report)
            raise ProjectUserAssociationError(
                f"Nenhum projeto encontrado com o nome exato: {project_name}"
            )

        if task_conflicts:
            write_json(args.report, report)
            raise ProjectUserAssociationError(
                "Atualizacao abortada: ha tarefas duplicadas que colidiriam "
                "ao trocar o user_id."
            )

        if args.commit:
            counts = report["counts"]
            counts["projects_updated"] = writer.update_projects_user(
                project_ids,
                target_user_id,
            )
            counts["tasks_updated"] = writer.update_tasks_user(
                project_ids,
                target_user_id,
            )
            writer.commit()
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
        description="Associa projetos por nome a um UID de usuario Supabase."
    )
    parser.add_argument(
        "--project-name",
        default=DEFAULT_PROJECT_NAME,
        help=f"Nome exato do projeto. Padrao: {DEFAULT_PROJECT_NAME}",
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"UID Supabase alvo. Padrao: {DEFAULT_USER_ID}",
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
        report = run_association(args)
    except ProjectUserAssociationError as exc:
        print(f"Erro de associacao: {exc}")
        return 2
    except Exception as exc:  # pragma: no cover - mantem stack curta para uso manual.
        print(f"Erro inesperado: {exc}")
        return 1

    counts = report["counts"]
    print(f"Modo: {report['mode']}")
    print(f"Projeto: {report['project_name']}")
    print(f"UID alvo: {report['target_user_id']}")
    print(f"Projetos encontrados: {counts['projects_matched']}")
    print(f"Projetos a atualizar: {counts['projects_would_update']}")
    print(f"Tarefas lidas: {counts['tasks_scanned']}")
    print(f"Tarefas a atualizar: {counts['tasks_would_update']}")
    if counts["task_conflicts"]:
        print(f"Conflitos de tarefas: {counts['task_conflicts']}")
    if report["mode"] == "commit":
        print(f"Projetos atualizados: {counts['projects_updated']}")
        print(f"Tarefas atualizadas: {counts['tasks_updated']}")
    print(f"Relatorio: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
