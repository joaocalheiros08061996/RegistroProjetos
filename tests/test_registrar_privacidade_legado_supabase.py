from argparse import Namespace
from pathlib import Path

import pytest

from automacoes.registrar_privacidade_legado_supabase import (
    LegacyPrivacyRegistrationError,
    parse_legacy_csv,
    run_registration,
)
from infra.security.privacy_audit import PrivacyAuditConfigError

USER_1 = "3a57b554-346e-492f-88a4-f1dbb7d5ba77"
USER_2 = "31f4c23f-426b-48f5-b158-c49924bd95c4"


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _args(csv_path: Path, report: Path, *, commit: bool = False) -> Namespace:
    return Namespace(
        csv=csv_path,
        reason="Usuarios existentes antes da publicacao do aviso.",
        policy_version="2026-06-01",
        report=report,
        commit=commit,
    )


def test_parse_legacy_csv_validates_rows_and_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "audit-secret")
    csv_path = _write_csv(
        tmp_path / "usuarios.csv",
        (
            "user_id,email\n"
            f"{USER_1},joao@example.com\n"
            "id-invalido,maria@example.com\n"
            f"{USER_1},outro@example.com\n"
            f"{USER_2},joao@example.com\n"
        ),
    )

    parsed = parse_legacy_csv(csv_path)

    assert [record.user_id for record in parsed.records] == [USER_1]
    assert len(parsed.records[0].email_hash) == 64
    assert [item["reason"] for item in parsed.skipped] == [
        "invalid_user_id",
        "duplicate_user_id",
        "duplicate_email",
    ]


def test_parse_legacy_csv_requires_expected_columns(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "audit-secret")
    csv_path = _write_csv(tmp_path / "usuarios.csv", "id,email\n1,a@example.com\n")

    with pytest.raises(LegacyPrivacyRegistrationError, match="user_id,email"):
        parse_legacy_csv(csv_path)


def test_run_registration_requires_policy_version(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "audit-secret")
    monkeypatch.delenv("PRIVACY_POLICY_VERSION", raising=False)
    csv_path = _write_csv(
        tmp_path / "usuarios.csv",
        f"user_id,email\n{USER_1},joao@example.com\n",
    )
    args = _args(csv_path, tmp_path / "report.json")
    args.policy_version = None

    with pytest.raises(PrivacyAuditConfigError, match="PRIVACY_POLICY_VERSION"):
        run_registration(args)


def test_run_registration_dry_run_does_not_require_database_url(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "audit-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    csv_path = _write_csv(
        tmp_path / "usuarios.csv",
        f"user_id,email\n{USER_1},joao@example.com\n",
    )
    report_path = tmp_path / "report.json"

    report = run_registration(_args(csv_path, report_path))

    assert report["mode"] == "dry-run"
    assert report["counts"] == {
        "records_ready": 1,
        "records_skipped": 0,
        "records_existing": 0,
        "records_inserted": 0,
    }
    assert report_path.exists()


def test_run_registration_commit_inserts_only_missing_legacy_pending_records(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "audit-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    csv_path = _write_csv(
        tmp_path / "usuarios.csv",
        f"user_id,email\n{USER_1},joao@example.com\n{USER_2},maria@example.com\n",
    )

    class FakeWriter:
        instance = None

        def __init__(self, database_url):
            self.database_url = database_url
            self.inserted = []
            self.committed = False
            self.rolled_back = False
            self.closed = False
            FakeWriter.instance = self

        def find_existing(self, user_id, policy_version):
            return "LEGACY_PENDING" if user_id == USER_1 else None

        def insert_legacy_pending(self, *, record, policy_version, reason):
            self.inserted.append((record, policy_version, reason))

        def commit(self):
            self.committed = True

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    report = run_registration(
        _args(csv_path, tmp_path / "report.json", commit=True),
        writer_cls=FakeWriter,
    )

    writer = FakeWriter.instance
    assert report["counts"]["records_existing"] == 1
    assert report["counts"]["records_inserted"] == 1
    assert writer.inserted[0][0].user_id == USER_2
    assert writer.committed is True
    assert writer.rolled_back is False
    assert writer.closed is True


def test_run_registration_rolls_back_on_insert_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVACY_AUDIT_HASH_SECRET", "audit-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    csv_path = _write_csv(
        tmp_path / "usuarios.csv",
        f"user_id,email\n{USER_1},joao@example.com\n",
    )

    class FailingWriter:
        instance = None

        def __init__(self, database_url):
            self.rolled_back = False
            self.closed = False
            FailingWriter.instance = self

        def find_existing(self, user_id, policy_version):
            return None

        def insert_legacy_pending(self, *, record, policy_version, reason):
            raise RuntimeError("falha simulada")

        def commit(self):
            raise AssertionError("commit nao deveria ocorrer")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    with pytest.raises(RuntimeError, match="falha simulada"):
        run_registration(
            _args(csv_path, tmp_path / "report.json", commit=True),
            writer_cls=FailingWriter,
        )

    assert FailingWriter.instance.rolled_back is True
    assert FailingWriter.instance.closed is True
