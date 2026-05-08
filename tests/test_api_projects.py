import pytest


AUTH_HEADER = {"Authorization": "Bearer test-user-123"}


def test_create_project_api(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto API",
            "project_type": "LAYOUT",
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
    assert "FTE deve ser maior que zero" in response.json()["detail"]


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
    assert listed_project["gut_score"] == 1
    assert listed_project["priority_level"] == 5
    assert listed_project["priority_label"] == "Prioridade 5"


def test_project_detail_api_returns_full_payload(client):
    project_response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Detalhe API",
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


@pytest.mark.parametrize("project_type", ["PADRONIZACAO", "TRY_OUT", "MELHORIA_PROC_NOVOS"])
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
