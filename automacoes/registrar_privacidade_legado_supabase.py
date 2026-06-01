#!/usr/bin/env python3
"""Registra usuarios legados como pendentes de ciencia do aviso de privacidade.

Dry-run seguro:
    python automacoes/registrar_privacidade_legado_supabase.py \
        --csv usuarios_legados.csv \
        --reason "Usuarios existentes antes da publicacao do aviso"

Gravacao real:
    python automacoes/registrar_privacidade_legado_supabase.py \
        --csv usuarios_legados.csv \
        --reason "Usuarios existentes antes da publicacao do aviso" \
        --commit
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automacoes.file_validation import validate_input_file
from infra.security.privacy_audit import (
    PrivacyAuditConfigError,
    configured_policy_version,
    privacy_audit_hash,
)

DEFAULT_REPORT = Path(__file__).with_name("registrar_privacidade_legado_report.json")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LegacyPrivacyRegistrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class LegacyPrivacyRecord:
    row: int
    user_id: str
    email_hash: str


@dataclass(frozen=True)
class ParsedLegacyPrivacyRecords:
    records: list[LegacyPrivacyRecord]
    skipped: list[dict[str, Any]]


def _normalize_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError("invalid_email")
    return email


def _normalize_user_id(value: str) -> str:
    try:
        return str(UUID(str(value or "").strip()))
    except ValueError as exc:
        raise ValueError("invalid_user_id") from exc


def parse_legacy_csv(csv_path: Path) -> ParsedLegacyPrivacyRecords:
    try:
        csv_path = validate_input_file(
            csv_path,
            allowed_suffixes={".csv"},
            description="CSV de usuarios legados",
        )
    except (FileNotFoundError, ValueError) as exc:
        raise LegacyPrivacyRegistrationError(str(exc)) from exc

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = {
            str(fieldname or "").strip().lower()
            for fieldname in (reader.fieldnames or [])
        }
        required = {"user_id", "email"}
        if not required.issubset(fieldnames):
            raise LegacyPrivacyRegistrationError(
                "CSV deve conter as colunas obrigatorias: user_id,email."
            )

        records: list[LegacyPrivacyRecord] = []
        skipped: list[dict[str, Any]] = []
        seen_user_ids: set[str] = set()
        seen_emails: set[str] = set()
        for row_number, raw_row in enumerate(reader, start=2):
            row = {
                str(key or "").strip().lower(): str(value or "")
                for key, value in raw_row.items()
            }
            if not any(value.strip() for value in row.values()):
                continue
            try:
                user_id = _normalize_user_id(row.get("user_id", ""))
                email = _normalize_email(row.get("email", ""))
            except ValueError as exc:
                skipped.append({"row": row_number, "reason": str(exc)})
                continue

            if user_id in seen_user_ids:
                skipped.append(
                    {"row": row_number, "user_id": user_id, "reason": "duplicate_user_id"}
                )
                continue
            if email in seen_emails:
                skipped.append(
                    {"row": row_number, "user_id": user_id, "reason": "duplicate_email"}
                )
                continue

            seen_user_ids.add(user_id)
            seen_emails.add(email)
            records.append(
                LegacyPrivacyRecord(
                    row=row_number,
                    user_id=user_id,
                    email_hash=privacy_audit_hash(email),
                )
            )

    return ParsedLegacyPrivacyRecords(records=records, skipped=skipped)


class SupabaseLegacyPrivacyWriter:
    def __init__(self, database_url: str):
        try:
            import psycopg2
        except ImportError as exc:
            raise LegacyPrivacyRegistrationError(
                "Dependencia ausente: instale psycopg2-binary com "
                "`pip install -r requirements.txt`."
            ) from exc
        self.conn = psycopg2.connect(database_url)

    def find_existing(self, user_id: str, policy_version: str) -> str | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select status
                from auth_privacy_acknowledgements
                where user_id = %s and policy_version = %s
                """,
                (user_id, policy_version),
            )
            row = cur.fetchone()
        return str(row[0]) if row else None

    def insert_legacy_pending(
        self,
        *,
        record: LegacyPrivacyRecord,
        policy_version: str,
        reason: str,
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into auth_privacy_acknowledgements (
                    user_id,
                    policy_version,
                    status,
                    source,
                    email_hash,
                    administrative_reason
                )
                values (%s, %s, 'LEGACY_PENDING', 'ADMIN_CSV', %s, %s)
                """,
                (record.user_id, policy_version, record.email_hash, reason),
            )

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)


def run_registration(
    args: argparse.Namespace,
    *,
    writer_cls: type[SupabaseLegacyPrivacyWriter] = SupabaseLegacyPrivacyWriter,
) -> dict[str, Any]:
    policy_version = configured_policy_version(args.policy_version)
    reason = str(args.reason or "").strip()
    if not reason:
        raise LegacyPrivacyRegistrationError("--reason deve ser informado.")
    if len(reason) > 1000:
        raise LegacyPrivacyRegistrationError("--reason excede 1000 caracteres.")

    parsed = parse_legacy_csv(args.csv)
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "commit" if args.commit else "dry-run",
        "csv": str(args.csv),
        "policy_version": policy_version,
        "administrative_reason": reason,
        "counts": {
            "records_ready": len(parsed.records),
            "records_skipped": len(parsed.skipped),
            "records_existing": 0,
            "records_inserted": 0,
        },
        "skipped": parsed.skipped,
    }

    if not args.commit:
        _write_json(args.report, report)
        return report

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise LegacyPrivacyRegistrationError(
            "DATABASE_URL nao definida. Configure no .env ou no ambiente."
        )

    writer = writer_cls(database_url)
    try:
        for record in parsed.records:
            if writer.find_existing(record.user_id, policy_version):
                report["counts"]["records_existing"] += 1
                continue
            writer.insert_legacy_pending(
                record=record,
                policy_version=policy_version,
                reason=reason,
            )
            report["counts"]["records_inserted"] += 1
        writer.commit()
    except Exception:
        writer.rollback()
        raise
    finally:
        writer.close()

    _write_json(args.report, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Registra usuarios legados como pendentes de ciencia de privacidade."
    )
    parser.add_argument("--csv", type=Path, required=True, help="CSV com colunas user_id,email.")
    parser.add_argument("--reason", required=True, help="Justificativa administrativa da carga.")
    parser.add_argument(
        "--policy-version",
        default=None,
        help="Versao do aviso. Padrao: PRIVACY_POLICY_VERSION.",
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
        help="Grava no banco. Sem esta flag, roda dry-run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv()
        report = run_registration(parse_args(argv))
    except (LegacyPrivacyRegistrationError, PrivacyAuditConfigError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report["counts"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
