from argparse import Namespace

from automacoes.padronizar_responsaveis_supabase import run_normalization


class FakeResponsibleWriter:
    last = None

    def __init__(self, database_url):
        self.database_url = database_url
        self.project_updates = []
        self.activity_updates = []
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.__class__.last = self

    def fetch_projects(self):
        return [
            {"id": 1, "responsible_login": "fagner"},
            {"id": 2, "responsible_login": "Jackson"},
        ]

    def fetch_activities(self):
        return [
            {"id": 10, "user_id": "JACKSON", "responsavel": ""},
            {"id": 11, "user_id": "jc", "responsavel": None},
            {
                "id": 12,
                "user_id": "3a57b554-346e-492f-88a4-f1dbb7d5ba77",
                "responsavel": "",
            },
        ]

    def update_project_responsible(self, project_id, responsible_login):
        self.project_updates.append((project_id, responsible_login))

    def update_activity_responsible(self, activity_id, user_id, responsavel):
        self.activity_updates.append((activity_id, user_id, responsavel))

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _args(tmp_path, *, commit=False):
    return Namespace(report=tmp_path / "report.json", commit=commit)


def test_responsible_normalization_dry_run_reports_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")

    report = run_normalization(
        _args(tmp_path),
        writer_cls=FakeResponsibleWriter,
    )

    counts = report["counts"]
    assert report["mode"] == "dry-run"
    assert counts["projects_would_update"] == 1
    assert counts["activities_rows_would_update"] == 2
    assert counts["activities_user_id_would_update"] == 2
    assert counts["activities_responsavel_would_update"] == 2
    assert FakeResponsibleWriter.last.project_updates == []
    assert FakeResponsibleWriter.last.activity_updates == []
    assert FakeResponsibleWriter.last.closed


def test_responsible_normalization_commit_updates_writer(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")

    report = run_normalization(
        _args(tmp_path, commit=True),
        writer_cls=FakeResponsibleWriter,
    )

    writer = FakeResponsibleWriter.last
    assert report["mode"] == "commit"
    assert report["counts"]["projects_updated"] == 1
    assert report["counts"]["activities_rows_updated"] == 2
    assert writer.project_updates == [(1, "Fagner")]
    assert writer.activity_updates == [
        (10, "Jackson", "Jackson"),
        (11, "João Calheiros", "João Calheiros"),
    ]
    assert writer.committed
    assert not writer.rolled_back
    assert writer.closed
