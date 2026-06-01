import pytest


AUTH_HEADER = {"Authorization": "Bearer test-user-123"}


def test_create_project_api(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto API",
            "project_type": "LAYOUT",
            "process_classification": "Processos novos",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-01-01T00:00:00",
            "planned_end": "2026-01-31T00:00:00",
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert "id" in body
    assert body["name"] == "Projeto API"
    assert body["task_count"] == 0


def test_create_project_invalid_fte_returns_422(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Invalido",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 0,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
        },
    )

    assert response.status_code == 422
    assert "fte" in str(response.json()["detail"]).lower()


def test_create_project_fractional_fte_returns_422(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto FTE Fracionado",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.2,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
        },
    )

    assert response.status_code == 422
    assert "FTE deve ser um numero inteiro" in str(response.json()["detail"])


def test_create_project_rejects_extra_fields(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Campo Extra",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
            "campo_extra": "nao permitido",
        },
    )

    assert response.status_code == 422


def test_create_project_rejects_long_text_and_invalid_cost(client):
    long_name = "P" * 161
    long_responsible = "R" * 121

    long_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": long_name,
            "project_type": "LAYOUT",
            "responsible_login": long_responsible,
            "fte": 1.0,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
        },
    )
    assert long_response.status_code == 422

    negative_cost_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Custo Negativo",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
            "estimated_cost": -1,
        },
    )
    assert negative_cost_response.status_code == 422


def test_create_project_rejects_fte_above_limit(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto FTE Alto",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 101,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
        },
    )

    assert response.status_code == 422


def test_create_project_without_auth_returns_401(client):
    response = client.post(
        "/projects/",
        json={
            "name": "Projeto Sem Auth",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
        },
    )

    assert response.status_code == 401


def test_create_project_with_invalid_auth_header_returns_401(client):
    response = client.post(
        "/projects/",
        headers={"Authorization": "InvalidHeader"},
        json={
            "name": "Projeto Auth Errado",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-02-01T00:00:00",
            "planned_end": "2026-02-10T00:00:00",
        },
    )

    assert response.status_code == 401


def test_list_projects_api_returns_user_projects(client):
    create_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Listagem API",
            "project_type": "LAYOUT",
            "process_classification": "Processos existentes",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-03-01T00:00:00",
            "planned_end": "2026-03-31T00:00:00",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    list_response = client.get("/projects/", headers=AUTH_HEADER)
    assert list_response.status_code == 200
    projects = list_response.json()
    listed_project = next(project for project in projects if project["id"] == created["id"])
    assert listed_project["process_classification"] == "Processos existentes"
    assert listed_project["gut_score"] == 1
    assert listed_project["priority_level"] == 5
    assert listed_project["priority_label"] == "Prioridade 5"
    assert listed_project["complexity_score"] == 1
    assert listed_project["complexity_label"] == "Complexidade 1"


def test_list_projects_api_returns_project_complexity(client):
    create_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Complexidade API",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-03-01T00:00:00",
            "planned_end": "2026-03-31T00:00:00",
            "objective_clarity": "Objetivo parcialmente definido",
            "method_clarity": "Métodos pouco definidos",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()

    list_response = client.get("/projects/", headers=AUTH_HEADER)
    assert list_response.status_code == 200
    projects = list_response.json()
    listed_project = next(project for project in projects if project["id"] == created["id"])

    assert listed_project["complexity_score"] == 3
    assert listed_project["complexity_label"] == "Complexidade 3"


def test_project_detail_api_returns_full_payload(client):
    project_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Detalhe API",
            "project_type": "LAYOUT",
            "process_classification": "Processos novos",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-04-01T00:00:00",
            "planned_end": "2026-04-30T00:00:00",
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-detalhe",
            "planned_start": "2026-04-02T00:00:00",
            "planned_end": "2026-04-10T00:00:00",
            "cost": 20.0,
        },
    )
    assert task_response.status_code == 200

    detail_response = client.get(f"/projects/{project_id}/detail", headers=AUTH_HEADER)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == project_id
    assert detail["name"] == "Projeto Detalhe API"
    assert detail["process_classification"] == "Processos novos"
    assert detail["task_count"] == 1
    assert detail["tasks"][0]["name"] == "task-detalhe"


def test_delete_project_api_removes_project_and_tasks(client):
    project_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Delete API",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-04-01T00:00:00",
            "planned_end": "2026-04-30T00:00:00",
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-remover",
            "planned_start": "2026-04-02T00:00:00",
            "planned_end": "2026-04-10T00:00:00",
            "cost": 20.0,
        },
    )
    assert task_response.status_code == 200

    delete_response = client.delete(f"/projects/{project_id}", headers=AUTH_HEADER)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    list_response = client.get("/projects/", headers=AUTH_HEADER)
    assert list_response.status_code == 200
    projects = list_response.json()
    assert not any(project["id"] == project_id for project in projects)

    detail_response = client.get(f"/projects/{project_id}/detail", headers=AUTH_HEADER)
    assert detail_response.status_code == 422


@pytest.mark.parametrize(
    "project_type",
    [
        "LAYOUT",
        "EXPORTACAO",
        "NORMATIZACAO",
        "PADRONIZACAO",
        "TRY_OUT",
        "MAPEAMENTO",
        "PECAS",
    ],
)
def test_create_project_api_accepts_new_project_types(client, project_type):
    create_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": f"Projeto {project_type}",
            "project_type": project_type,
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-05-01T00:00:00",
            "planned_end": "2026-05-31T00:00:00",
        },
    )

    assert create_response.status_code == 200
    created_id = create_response.json()["id"]

    list_response = client.get("/projects/", headers=AUTH_HEADER)
    assert list_response.status_code == 200
    projects = list_response.json()
    created = next(project for project in projects if project["id"] == created_id)
    assert created["project_type"] == project_type


@pytest.mark.parametrize("project_type", ["MELHORIA", "MELHORIA_PROC_NOVOS"])
def test_create_project_api_rejects_legacy_project_types(client, project_type):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": f"Projeto {project_type}",
            "project_type": project_type,
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-05-01T00:00:00",
            "planned_end": "2026-05-31T00:00:00",
        },
    )

    assert response.status_code == 422
    assert "Tipo de projeto legado" in response.json()["detail"]


def test_create_project_api_rejects_invalid_process_classification(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Classificacao Invalida",
            "project_type": "LAYOUT",
            "process_classification": "Processo antigo",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-06-01T00:00:00",
            "planned_end": "2026-06-30T00:00:00",
        },
    )

    assert response.status_code == 422


def test_sql_like_project_name_is_treated_as_text(client):
    project_name = "Projeto'; DROP TABLE projects; --"
    create_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": project_name,
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-06-01T00:00:00",
            "planned_end": "2026-06-30T00:00:00",
        },
    )
    assert create_response.status_code == 200
    project_id = create_response.json()["id"]

    list_response = client.get("/projects/", headers=AUTH_HEADER)
    assert list_response.status_code == 200
    assert any(
        project["id"] == project_id and project["name"] == project_name
        for project in list_response.json()
    )

    delete_response = client.delete(f"/projects/{project_id}", headers=AUTH_HEADER)
    assert delete_response.status_code == 200
