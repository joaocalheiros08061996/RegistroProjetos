from argparse import Namespace
from datetime import datetime, timedelta
import json

import pytest
from openpyxl import Workbook

from automacoes.importar_a3_supabase import MigrationError, normalize_key
from automacoes.importar_a3_2026_supabase import (
    DEFAULT_WORKBOOK,
    SOLDAGEM_PROJECT_NAME,
    build_records_2026,
    external_project_keys,
    project_type_2026,
    read_excel_records_2026,
    run_import,
    time_entries_ready,
)


def _project_row(**overrides):
    row = {
        "PROJETOS": "Projeto Novo",
        "TIPO DE PROJETOS": "Mapeamento de Processos",
        "RESPONSÁVEL": "João Calheiros",
        "FTes": 1,
        "DATA INÍCIO PLANEJ": datetime(2026, 2, 16),
        "DATA FIM PLANEJ": datetime(2026, 3, 31),
        "GRAVIDADE": "2 - Pouco grave",
        "URGÊNCIA": "2 - Pouco urgente",
        "TENDêNCIA": "3 - Piora em médio prazo",
        "OBJETIVOS": "1 - Objetivo totalmente definido",
        "MÉTODOS": "3 - Métodos parcialmente conhecidos",
    }
    row.update(overrides)
    return row


def _task_row(**overrides):
    row = {
        "PROJETO": "Projeto Novo",
        "TAREFA": "Desenvolvimento",
        "SUBTAREFA": "Aplicação Web",
        "RESPONSÁVEL": "João Calheiros",
        "DATA INÍCIO PLANEJ": datetime(2026, 2, 16),
        "DATA FIM DO PLANEJ": datetime(2026, 2, 20),
        "DATA INÍCIO REAL": datetime(2026, 2, 16),
        "DIAS REAIS": 4,
        "PERCENTUAL REALIZADO": 1,
    }
    row.update(overrides)
    return row


def _write_workbook(tmp_path, project_rows, task_rows):
    workbook = Workbook()
    projects = workbook.active
    projects.title = "PROJETOS_2026"
    projects.append(
        [
            "PROJETOS",
            "TIPO DE PROJETOS ",
            "RESPONSÁVEL",
            "FTes",
            "DATA INÍCIO PLANEJ",
            "DATA FIM PLANEJ",
            "GRAVIDADE",
            "URGÊNCIA",
            "TENDêNCIA",
            "OBJETIVOS",
            "MÉTODOS ",
        ]
    )
    for row in project_rows:
        projects.append(
            [
                row.get("PROJETOS"),
                row.get("TIPO DE PROJETOS"),
                row.get("RESPONSÁVEL"),
                row.get("FTes"),
                row.get("DATA INÍCIO PLANEJ"),
                row.get("DATA FIM PLANEJ"),
                row.get("GRAVIDADE"),
                row.get("URGÊNCIA"),
                row.get("TENDêNCIA"),
                row.get("OBJETIVOS"),
                row.get("MÉTODOS"),
            ]
        )

    tasks = workbook.create_sheet("TAREFAS_2026")
    tasks.append(
        [
            "PROJETO",
            "TIPO DE PROJETO",
            "TAREFA",
            "SUBTAREFA",
            "RESPONSÁVEL",
            "DATA INÍCIO PLANEJ",
            "DIAS PLANEJADOS ",
            "DATA FIM DO PLANEJ",
            "DATA INÍCIO REAL",
            "DIAS REAIS",
            "DATA FIM DO REAL",
            "PERCENTUAL REALIZADO",
        ]
    )
    for row in task_rows:
        tasks.append(
            [
                row.get("PROJETO"),
                row.get("TIPO DE PROJETO"),
                row.get("TAREFA"),
                row.get("SUBTAREFA"),
                row.get("RESPONSÁVEL"),
                row.get("DATA INÍCIO PLANEJ"),
                row.get("DIAS PLANEJADOS"),
                row.get("DATA FIM DO PLANEJ"),
                row.get("DATA INÍCIO REAL"),
                row.get("DIAS REAIS"),
                row.get("DATA FIM DO REAL"),
                row.get("PERCENTUAL REALIZADO"),
            ]
        )

    workbook_path = tmp_path / "a3_2026.xlsx"
    workbook.save(workbook_path)
    return workbook_path


def test_default_workbook_uses_2026_file():
    assert DEFAULT_WORKBOOK.name == "A3 - Gerenciamento de Projetos (2026).xlsx"


def test_project_type_2026_maps_known_2026_labels():
    assert project_type_2026("Mapeamento de Processos") == ("MAPEAMENTO", None)
    assert project_type_2026("Padronização") == ("PADRONIZACAO", None)


def test_build_records_2026_keeps_soldagem_tasks_as_external_project():
    records = build_records_2026(
        project_rows=[
            _project_row(_row_number=2, **{"RESPONSÁVEL": "JOÃO PAULO"}),
            _project_row(
                _row_number=3,
                PROJETOS="Treinamento",
                **{"TIPO DE PROJETOS": "Padronização"},
            ),
        ],
        task_rows=[
            _task_row(_row_number=2),
            _task_row(
                _row_number=3,
                PROJETO=SOLDAGEM_PROJECT_NAME,
                TAREFA="Avaliação Diagnóstica dos Soldadores: Programa de Soldagem",
                SUBTAREFA="ROGERIO DE ASSIS KUBIAK",
            ),
            _task_row(
                _row_number=4,
                PROJETO="Projeto Desconhecido",
                TAREFA="Ignorada",
                SUBTAREFA="NA",
            ),
            _task_row(
                _row_number=5,
                **{"DATA INÍCIO PLANEJ": "#REF!"},
            ),
        ],
        year=2026,
    )

    assert len(records.projects) == 2
    assert [project.project_type for project in records.projects] == [
        "MAPEAMENTO",
        "PADRONIZACAO",
    ]
    assert records.projects[0].responsible_login == "João Paulo"
    assert [task.name for task in records.tasks] == [
        "Desenvolvimento - Aplicação Web",
        "Avaliação Diagnóstica dos Soldadores: Programa de Soldagem - ROGERIO DE ASSIS KUBIAK",
    ]
    assert [task.actual_seconds for task in records.tasks] == [345600, 345600]
    assert normalize_key(SOLDAGEM_PROJECT_NAME) in external_project_keys(records)
    assert time_entries_ready(records) == 2
    assert [item["reason"] for item in records.skipped_tasks] == [
        "project_not_imported",
        "ref_error",
    ]


def test_read_real_2026_workbook_counts_current_valid_rows():
    records = read_excel_records_2026(DEFAULT_WORKBOOK, year=2026)

    assert len(records.projects) == 2
    assert len(records.tasks) == 40
    assert time_entries_ready(records) == 38
    assert len(records.skipped_projects) == 0
    assert len(records.skipped_tasks) == 0


class FakeWriter:
    project_lookup = {}
    task_lookup = {}
    time_entry_lookup = set()
    last = None

    def __init__(self, database_url):
        self.database_url = database_url
        self.project_lookup = dict(self.__class__.project_lookup)
        self.task_lookup = dict(self.__class__.task_lookup)
        self.time_entry_lookup = set(self.__class__.time_entry_lookup)
        self.inserted_projects = []
        self.inserted_tasks = []
        self.inserted_time_entries = []
        self.next_project_id = 1000
        self.next_task_id = 2000
        self.next_time_entry_id = 3000
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.__class__.last = self

    @staticmethod
    def project_key(user_id, name, year):
        return (user_id, normalize_key(name), year)

    @staticmethod
    def task_key(project_id, user_id, name):
        return (project_id, user_id, name)

    @staticmethod
    def time_entry_key(task_id, task):
        end_time = task.actual_start + timedelta(seconds=task.actual_seconds)
        return (task_id, task.actual_start, end_time)

    def close(self):
        self.closed = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def find_project_by_name_and_year(self, user_id, name, year):
        value = self.project_lookup.get(self.project_key(user_id, name, year))
        if value == "AMBIGUOUS":
            raise MigrationError("Projeto ambiguo")
        return value

    def find_task_by_name(self, project_id, user_id, name):
        return self.task_lookup.get(self.task_key(project_id, user_id, name))

    def time_entry_exists(self, task_id, task):
        if task.actual_start is None or task.actual_seconds <= 0:
            return False
        return self.time_entry_key(task_id, task) in self.time_entry_lookup

    def insert_project(self, user_id, project):
        project_id = self.next_project_id
        self.next_project_id += 1
        self.project_lookup[self.project_key(user_id, project.name, project.planned_start.year)] = project_id
        self.inserted_projects.append((project_id, project))
        return project_id

    def insert_task(self, user_id, project_id, task):
        task_id = self.next_task_id
        self.next_task_id += 1
        self.task_lookup[self.task_key(project_id, user_id, task.name)] = task_id
        self.inserted_tasks.append((task_id, project_id, task))
        return task_id

    def insert_time_entry(self, task_id, task):
        entry_id = self.next_time_entry_id
        self.next_time_entry_id += 1
        self.time_entry_lookup.add(self.time_entry_key(task_id, task))
        self.inserted_time_entries.append((entry_id, task_id, task))
        return entry_id


def _reset_fake_writer():
    FakeWriter.project_lookup = {}
    FakeWriter.task_lookup = {}
    FakeWriter.time_entry_lookup = set()
    FakeWriter.last = None


def test_run_import_commit_resolves_external_project_and_avoids_duplicates(
    monkeypatch,
    tmp_path,
):
    _reset_fake_writer()
    user_id = "user-123"
    existing_task_name = "Avaliação Diagnóstica dos Soldadores: Programa de Soldagem - ROGERIO"
    existing_task_start = datetime(2026, 1, 6)
    workbook_path = _write_workbook(
        tmp_path,
        [_project_row()],
        [
            _task_row(),
            _task_row(
                PROJETO=SOLDAGEM_PROJECT_NAME,
                TAREFA="Avaliação Diagnóstica dos Soldadores: Programa de Soldagem",
                SUBTAREFA="ROGERIO",
                **{
                    "DATA INÍCIO PLANEJ": existing_task_start,
                    "DATA FIM DO PLANEJ": existing_task_start,
                    "DATA INÍCIO REAL": existing_task_start,
                    "DIAS REAIS": 1,
                },
            ),
        ],
    )

    external_project_id = 501
    existing_task_id = 601
    FakeWriter.project_lookup = {
        FakeWriter.project_key(user_id, SOLDAGEM_PROJECT_NAME, 2025): external_project_id
    }
    FakeWriter.task_lookup = {
        FakeWriter.task_key(external_project_id, user_id, existing_task_name): existing_task_id
    }
    fake_entry_task = build_records_2026(
        [],
        [
            _task_row(
                PROJETO=SOLDAGEM_PROJECT_NAME,
                TAREFA="Avaliação Diagnóstica dos Soldadores: Programa de Soldagem",
                SUBTAREFA="ROGERIO",
                **{
                    "DATA INÍCIO PLANEJ": existing_task_start,
                    "DATA FIM DO PLANEJ": existing_task_start,
                    "DATA INÍCIO REAL": existing_task_start,
                    "DIAS REAIS": 1,
                },
            )
        ],
    ).tasks[0]
    FakeWriter.time_entry_lookup = {
        FakeWriter.time_entry_key(existing_task_id, fake_entry_task)
    }

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    report = run_import(
        Namespace(
            workbook=workbook_path,
            user_id=user_id,
            year=2026,
            report=tmp_path / "report.json",
            commit=True,
        ),
        writer_cls=FakeWriter,
    )

    writer = FakeWriter.last
    assert writer.committed is True
    assert writer.rolled_back is False
    assert len(writer.inserted_projects) == 1
    assert len(writer.inserted_tasks) == 1
    assert len(writer.inserted_time_entries) == 1
    assert report["counts"]["external_projects_resolved"] == 1
    assert report["counts"]["projects_inserted"] == 1
    assert report["counts"]["tasks_existing"] == 1
    assert report["counts"]["tasks_inserted"] == 1
    assert report["counts"]["time_entries_existing"] == 1
    assert report["counts"]["time_entries_inserted"] == 1


@pytest.mark.parametrize("lookup_value", [None, "AMBIGUOUS"])
def test_run_import_commit_fails_before_insert_when_external_project_is_missing_or_ambiguous(
    monkeypatch,
    tmp_path,
    lookup_value,
):
    _reset_fake_writer()
    user_id = "user-123"
    workbook_path = _write_workbook(
        tmp_path,
        [_project_row()],
        [
            _task_row(
                PROJETO=SOLDAGEM_PROJECT_NAME,
                TAREFA="Avaliação Diagnóstica dos Soldadores: Programa de Soldagem",
                SUBTAREFA="ROGERIO",
            )
        ],
    )
    if lookup_value is not None:
        FakeWriter.project_lookup = {
            FakeWriter.project_key(user_id, SOLDAGEM_PROJECT_NAME, 2025): lookup_value
        }

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    with pytest.raises(MigrationError):
        run_import(
            Namespace(
                workbook=workbook_path,
                user_id=user_id,
                year=2026,
                report=tmp_path / "report.json",
                commit=True,
            ),
            writer_cls=FakeWriter,
        )

    writer = FakeWriter.last
    assert writer.inserted_projects == []
    assert writer.inserted_tasks == []
    assert writer.inserted_time_entries == []
    assert writer.rolled_back is True
    assert writer.committed is False


def test_run_import_dry_run_without_database_writes_report(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    workbook_path = _write_workbook(
        tmp_path,
        [_project_row()],
        [
            _task_row(),
            _task_row(
                PROJETO=SOLDAGEM_PROJECT_NAME,
                TAREFA="Avaliação Diagnóstica dos Soldadores: Programa de Soldagem",
                SUBTAREFA="ROGERIO",
            ),
        ],
    )
    report_path = tmp_path / "report.json"

    report = run_import(
        Namespace(
            workbook=workbook_path,
            user_id="user-123",
            year=2026,
            report=report_path,
            commit=False,
        )
    )

    assert report["mode"] == "dry-run"
    assert report["counts"]["projects_ready"] == 1
    assert report["counts"]["tasks_ready"] == 2
    assert report["counts"]["time_entries_ready"] == 2
    assert report["counts"]["database_checked"] is False
    assert json.loads(report_path.read_text(encoding="utf-8"))["year"] == 2026
