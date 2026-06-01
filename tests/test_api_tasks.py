from urllib.parse import quote


AUTH_HEADER = {"Authorization": "Bearer test-user-123"}


def create_project(client):
    response = client.post(
        "/projects/",
        headers=AUTH_HEADER,
        json={
            "name": "Projeto Tasks",
            "project_type": "LAYOUT",
            "responsible_login": "user1",
            "fte": 1.0,
            "planned_start": "2026-01-01T00:00:00",
            "planned_end": "2026-01-31T00:00:00",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_create_task_api(client):
    project_id = create_project(client)

    response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-a",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
            "cost": 100.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "task-a"
    assert body["percent_completed"] == 0.0


def test_list_tasks_api(client):
    project_id = create_project(client)

    client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-list",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )

    response = client.get(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "task-list"


def test_get_task_api(client):
    project_id = create_project(client)

    client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-detail",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )

    response = client.get(
        f"/projects/{project_id}/tasks/task-detail",
        headers=AUTH_HEADER,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "task-detail"


def test_start_and_stop_task_api(client):
    project_id = create_project(client)

    client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-time",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )

    start_resp = client.post(
        f"/projects/{project_id}/tasks/task-time/start",
        headers=AUTH_HEADER,
    )
    assert start_resp.status_code == 200

    stop_resp = client.post(
        f"/projects/{project_id}/tasks/task-time/stop",
        headers=AUTH_HEADER,
    )
    assert stop_resp.status_code == 200
    assert stop_resp.json()["duration_seconds"] >= 0


def test_complete_task_api(client):
    project_id = create_project(client)

    client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-done",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )

    response = client.post(
        f"/projects/{project_id}/tasks/task-done/complete",
        headers=AUTH_HEADER,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_delete_task_api(client):
    project_id = create_project(client)

    create_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-delete",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )
    assert create_response.status_code == 200

    delete_response = client.delete(
        f"/projects/{project_id}/tasks/task-delete",
        headers=AUTH_HEADER,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    list_response = client.get(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
    )
    assert list_response.status_code == 200
    assert list_response.json() == []

    detail_response = client.get(
        f"/projects/{project_id}/tasks/task-delete",
        headers=AUTH_HEADER,
    )
    assert detail_response.status_code == 422


def test_create_task_rejects_long_name_and_negative_cost(client):
    project_id = create_project(client)

    long_name_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "T" * 161,
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )
    assert long_name_response.status_code == 422

    negative_cost_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": "task-cost",
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
            "cost": -1,
        },
    )
    assert negative_cost_response.status_code == 422


def test_task_path_rejects_name_above_limit(client):
    project_id = create_project(client)
    long_name = quote("T" * 161)

    response = client.get(
        f"/projects/{project_id}/tasks/{long_name}",
        headers=AUTH_HEADER,
    )

    assert response.status_code == 422


def test_sql_like_task_name_is_treated_as_text(client):
    project_id = create_project(client)
    task_name = "task'; DROP TABLE tasks; --"
    encoded_name = quote(task_name, safe="")

    create_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=AUTH_HEADER,
        json={
            "name": task_name,
            "planned_start": "2026-01-02T00:00:00",
            "planned_end": "2026-01-05T00:00:00",
        },
    )
    assert create_response.status_code == 200

    detail_response = client.get(
        f"/projects/{project_id}/tasks/{encoded_name}",
        headers=AUTH_HEADER,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == task_name

    delete_response = client.delete(
        f"/projects/{project_id}/tasks/{encoded_name}",
        headers=AUTH_HEADER,
    )
    assert delete_response.status_code == 200
