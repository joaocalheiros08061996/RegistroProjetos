from argparse import Namespace

import pytest

from automacoes.associar_projeto_usuario_supabase import (
    DEFAULT_PROJECT_NAME,
    DEFAULT_USER_ID,
    ProjectUserAssociationError,
    run_association,
)


OTHER_USER_ID = "11111111-1111-4111-8111-111111111111"


class FakeProjectUserAssociator:
    last = None
    task_conflicts = []

    def __init__(self, database_url):
        self.database_url = database_url
        self.project_updates = []
        self.task_updates = []
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.__class__.last = self

    def fetch_projects_by_name(self, project_name):
        self.project_name = project_name
        return [
            {
                "id": 10,
                "name": DEFAULT_PROJECT_NAME,
                "user_id": OTHER_USER_ID,
                "responsible_login": "Joao",
            },
            {
                "id": 11,
                "name": DEFAULT_PROJECT_NAME,
                "user_id": DEFAULT_USER_ID,
                "responsible_login": "Joao",
            },
        ]

    def fetch_task_owner_counts(self, project_ids):
        self.project_ids = project_ids
        return [
            {"project_id": 10, "user_id": OTHER_USER_ID, "task_count": 3},
            {"project_id": 11, "user_id": DEFAULT_USER_ID, "task_count": 2},
        ]

    def fetch_task_name_conflicts(self, project_ids):
        return list(self.__class__.task_conflicts)

    def update_projects_user(self, project_ids, user_id):
        self.project_updates.append((project_ids, user_id))
        return 1

    def update_tasks_user(self, project_ids, user_id):
        self.task_updates.append((project_ids, user_id))
        return 3

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _args(tmp_path, *, commit=False, user_id=DEFAULT_USER_ID):
    return Namespace(
        project_name=DEFAULT_PROJECT_NAME,
        user_id=user_id,
        report=tmp_path / "report.json",
        commit=commit,
    )


def test_project_user_association_dry_run_reports_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    FakeProjectUserAssociator.task_conflicts = []

    report = run_association(
        _args(tmp_path),
        writer_cls=FakeProjectUserAssociator,
    )

    writer = FakeProjectUserAssociator.last
    assert report["mode"] == "dry-run"
    assert report["project_name"] == DEFAULT_PROJECT_NAME
    assert report["target_user_id"] == DEFAULT_USER_ID
    assert report["can_commit"]
    assert report["counts"]["projects_matched"] == 2
    assert report["counts"]["projects_would_update"] == 1
    assert report["counts"]["tasks_scanned"] == 5
    assert report["counts"]["tasks_would_update"] == 3
    assert writer.project_updates == []
    assert writer.task_updates == []
    assert not writer.committed
    assert writer.closed
    assert _args(tmp_path).report.exists()


def test_project_user_association_commit_updates_projects_and_tasks(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    FakeProjectUserAssociator.task_conflicts = []

    report = run_association(
        _args(tmp_path, commit=True),
        writer_cls=FakeProjectUserAssociator,
    )

    writer = FakeProjectUserAssociator.last
    assert report["mode"] == "commit"
    assert report["counts"]["projects_updated"] == 1
    assert report["counts"]["tasks_updated"] == 3
    assert writer.project_updates == [([10, 11], DEFAULT_USER_ID)]
    assert writer.task_updates == [([10, 11], DEFAULT_USER_ID)]
    assert writer.committed
    assert not writer.rolled_back
    assert writer.closed


def test_project_user_association_rejects_invalid_user_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")

    with pytest.raises(ProjectUserAssociationError, match="UUID valido"):
        run_association(
            _args(tmp_path, user_id="usuario-sem-uuid"),
            writer_cls=FakeProjectUserAssociator,
        )


def test_project_user_association_aborts_commit_on_task_conflicts(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    FakeProjectUserAssociator.task_conflicts = [
        {
            "project_id": 10,
            "name": "Tarefa repetida",
            "task_count": 2,
            "task_ids": [100, 101],
            "user_ids": [OTHER_USER_ID, DEFAULT_USER_ID],
        }
    ]

    with pytest.raises(ProjectUserAssociationError, match="tarefas duplicadas"):
        run_association(
            _args(tmp_path, commit=True),
            writer_cls=FakeProjectUserAssociator,
        )

    writer = FakeProjectUserAssociator.last
    assert writer.project_updates == []
    assert writer.task_updates == []
    assert writer.rolled_back
    assert writer.closed
    FakeProjectUserAssociator.task_conflicts = []
