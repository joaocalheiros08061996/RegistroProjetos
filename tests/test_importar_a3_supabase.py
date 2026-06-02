from datetime import datetime
import json

import pytest

from automacoes.importar_a3_supabase import (
    MigrationError,
    build_records,
    days_to_seconds,
    load_manifest,
    map_method,
    map_objective,
    map_project_type,
    map_severity,
    map_task_status,
    parse_excel_datetime,
)


def test_excel_serial_and_day_effort_conversion():
    assert parse_excel_datetime(45355) == datetime(2024, 3, 4)
    assert days_to_seconds(2) == 172800
    assert days_to_seconds("1,5") == 129600
    assert days_to_seconds("não") == 0


def test_portuguese_labels_are_mapped_to_app_enums():
    assert map_project_type("Padronização") == "PADRONIZACAO"
    assert map_project_type("Peças em Geral") == "PECAS"
    assert map_severity("4 - Muito grave") == "Muito grave"
    assert map_objective("2 - Objetivo claro com pequenas ambiguidades") == (
        "Objetivo claro com pequenas ambiguidades"
    )
    assert map_method("3 - Métodos parcialmente conhecidos") == (
        "Métodos parcialmente conhecidos"
    )


@pytest.mark.parametrize(
    "project_type",
    [
        "Melhoria",
        "Melhoria Contínua dos Processos",
        "Melhoria de Proc Novos",
        "MELHORIA",
        "MELHORIA_PROC_NOVOS",
    ],
)
def test_legacy_project_types_are_not_imported_as_new_projects(project_type):
    with pytest.raises(MigrationError, match="Tipo de projeto legado"):
        map_project_type(project_type)


def test_task_status_mapping_uses_real_effort_for_non_completed_tasks():
    assert map_task_status("Concluído", 0) == "COMPLETED"
    assert map_task_status("Não iniciado", 0) == "PLANNED"
    assert map_task_status("Atrasado", 0) == "PLANNED"
    assert map_task_status("Atrasado", 3600) == "PAUSED"
    assert map_task_status("", 3600) == "PAUSED"


def test_build_records_skips_unclassified_projects_and_their_tasks():
    records = build_records(
        project_rows=[
            {
                "ID": 1,
                "Projeto": "Projeto Classificado",
                "Responsável": "fagner",
                "FTEs": 1,
                "Valor previsto": 1000,
                "Data Início Planej.": 45355,
                "Data Fim Planej.": 45360,
            },
            {
                "ID": 2,
                "Projeto": "Projeto Sem Classificacao",
                "Responsável": "Fabricio",
                "FTEs": 1,
                "Valor previsto": 0,
                "Data Início Planej.": 45355,
                "Data Fim Planej.": 45360,
            },
        ],
        task_rows=[
            {
                "Coluna1": "1.1",
                "Projeto": "Projeto Classificado",
                "Tarefa": "Projetar Gabarito",
                "Data Início Planej.": 45355,
                "Data Fim Planej.": 45356,
                "Data Início Real": 45355,
                "Esforço Real": 2,
                "Status": "Concluído",
                "% Finalizado": 1,
                "Valor previsto": 500,
            },
            {
                "Coluna1": "2.1",
                "Projeto": "Projeto Sem Classificacao",
                "Tarefa": "Tarefa ignorada",
                "Data Início Planej.": 45355,
                "Data Fim Planej.": 45356,
                "Esforço Real": 1,
                "Status": "Concluído",
            },
        ],
        classified_rows=[
            {
                "PROJETOS": "Projeto Classificado",
                "TIPO DE PROJETOS": "Padronização",
                "RESPONSÁVEL": "Evandro",
                "FTes": 1,
                "DATA INÍCIO PLANEJ": 45355,
                "DATA FIM PLANEJ": 45360,
                "GRAVIDADE": "4 - Muito grave",
                "URGÊNCIA": "3 - Urgente",
                "TENDêNCIA": "4 - Piora em curto prazo",
                "OBJETIVOS": "2 - Objetivo claro com pequenas ambiguidades",
                "MÉTODOS": "2 - Métodos conhecidos com pequenas adaptações",
            }
        ],
    )

    assert [project.source_id for project in records.projects] == ["1"]
    assert records.projects[0].responsible_login == "Fagner"
    assert records.skipped_projects == [
        {
            "source_id": "2",
            "name": "Projeto Sem Classificacao",
            "reason": "missing_classification",
        }
    ]
    assert len(records.tasks) == 1
    task = records.tasks[0]
    assert task.source_id == "1.1"
    assert task.source_project_id == "1"
    assert task.status == "COMPLETED"
    assert task.actual_seconds == 172800
    assert task.actual_start == datetime(2024, 3, 4)
    assert records.skipped_tasks[0]["reason"] == "project_not_imported"


def test_not_started_task_without_dates_uses_project_dates():
    records = build_records(
        project_rows=[
            {
                "ID": 1,
                "Projeto": "Projeto A",
                "Responsável": "Evandro",
                "FTEs": 1,
                "Data Início Planej.": 45355,
                "Data Fim Planej.": 45360,
            }
        ],
        task_rows=[
            {
                "Coluna1": "1.2",
                "Projeto": "Projeto A",
                "Tarefa": "TRY OUT",
                "Data Início Planej.": "não",
                "Data Fim Planej.": None,
                "Esforço Real": None,
                "Status": "Não iniciado",
            }
        ],
        classified_rows=[
            {
                "PROJETOS": "Projeto A",
                "TIPO DE PROJETOS": "Padronização",
                "GRAVIDADE": "4 - Muito grave",
                "URGÊNCIA": "3 - Urgente",
                "TENDêNCIA": "4 - Piora em curto prazo",
                "OBJETIVOS": "2 - Objetivo claro com pequenas ambiguidades",
                "MÉTODOS": "2 - Métodos conhecidos com pequenas adaptações",
            }
        ],
    )

    task = records.tasks[0]
    assert task.planned_start == datetime(2024, 3, 4)
    assert task.planned_end == datetime(2024, 3, 9)
    assert task.status == "PLANNED"
    assert task.actual_seconds == 0


def test_manifest_rejects_different_user_id(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"user_id": "user-a"}), encoding="utf-8")

    with pytest.raises(MigrationError):
        load_manifest(manifest, "user-b")
