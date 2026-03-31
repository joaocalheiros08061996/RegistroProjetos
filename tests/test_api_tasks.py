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
