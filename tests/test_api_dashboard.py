from datetime import datetime

import application.services as services_module


def _create_project_and_task(
    client,
    auth_header: dict,
    *,
    project_name: str,
    project_type: str,
    task_name: str,
) -> int:
    project_response = client.post(
        "/projects/",
        headers=auth_header,
        json={
            "name": project_name,
            "project_type": project_type,
            "responsible_login": "user",
            "fte": 1.0,
            "planned_start": "2026-01-01T00:00:00",
            "planned_end": "2026-02-01T00:00:00",
        },
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/projects/{project_id}/tasks/",
        headers=auth_header,
        json={
            "name": task_name,
            "planned_start": "2026-01-01T00:00:00",
            "planned_end": "2026-01-20T00:00:00",
            "cost": 0.0,
        },
    )
    assert task_response.status_code == 200
    return project_id


def _patch_utcnow(monkeypatch, values: list[datetime]) -> None:
    class _FakeDatetime:
        _values = list(values)

        @classmethod
        def utcnow(cls):
            if not cls._values:
                raise AssertionError("Sem valores para datetime.utcnow()")
            return cls._values.pop(0)

        @classmethod
        def now(cls, tz=None):
            current = cls.utcnow()
            if tz is None:
                return current
            return current.replace(tzinfo=tz)

    monkeypatch.setattr(services_module, "datetime", _FakeDatetime)


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard/avg-real-days-by-project-type")
    assert response.status_code == 401


def test_dashboard_returns_global_average_across_users_and_ignores_open_entries(client, monkeypatch):
    user_1 = {"Authorization": "Bearer user-1"}
    user_2 = {"Authorization": "Bearer user-2"}

    project_1 = _create_project_and_task(
        client,
        user_1,
        project_name="Projeto U1",
        project_type="LAYOUT",
        task_name="task-u1",
    )
    project_2 = _create_project_and_task(
        client,
        user_2,
        project_name="Projeto U2",
        project_type="LAYOUT",
        task_name="task-u2",
    )
    project_3 = _create_project_and_task(
        client,
        user_2,
        project_name="Projeto U2 Open",
        project_type="EXPORTACAO",
        task_name="task-open",
    )

    _patch_utcnow(
        monkeypatch,
        [
            datetime(2026, 1, 1, 8, 0, 0),
            datetime(2026, 1, 3, 8, 0, 0),  # 2 dias no projeto 1
        ],
    )
    start_p1 = client.post(f"/projects/{project_1}/tasks/task-u1/start", headers=user_1)
    stop_p1 = client.post(f"/projects/{project_1}/tasks/task-u1/stop", headers=user_1)
    assert start_p1.status_code == 200
    assert stop_p1.status_code == 200

    _patch_utcnow(
        monkeypatch,
        [
            datetime(2026, 1, 4, 8, 0, 0),
            datetime(2026, 1, 8, 8, 0, 0),  # 4 dias no projeto 2
        ],
    )
    start_p2 = client.post(f"/projects/{project_2}/tasks/task-u2/start", headers=user_2)
    stop_p2 = client.post(f"/projects/{project_2}/tasks/task-u2/stop", headers=user_2)
    assert start_p2.status_code == 200
    assert stop_p2.status_code == 200

    _patch_utcnow(
        monkeypatch,
        [datetime(2026, 1, 10, 8, 0, 0)],
    )
    start_open = client.post(f"/projects/{project_3}/tasks/task-open/start", headers=user_2)
    assert start_open.status_code == 200

    response = client.get(
        "/dashboard/avg-real-days-by-project-type",
        headers=user_1,
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["chart"] == "avg_real_days_by_project_type"
    assert len(payload["items"]) == 1

    layout_item = payload["items"][0]
    assert layout_item["project_type"] == "LAYOUT"
    assert layout_item["project_type_label"] == "LAYOUT"
    assert layout_item["average_days"] == 3.0


def test_dashboard_projects_by_responsible_returns_global_projects(client):
    user_1 = {"Authorization": "Bearer user-1"}
    user_2 = {"Authorization": "Bearer user-2"}

    project_1_response = client.post(
        "/projects/",
        headers=user_1,
        json={
            "name": "Projeto Global Alice",
            "project_type": "LAYOUT",
            "responsible_login": "alice",
            "fte": 1.0,
            "planned_start": "2026-05-10T00:00:00",
            "planned_end": "2026-05-20T00:00:00",
            "objective_clarity": "Objetivo parcialmente definido",
            "method_clarity": "Métodos pouco definidos",
            "estimated_cost": 1500.0,
        },
    )
    assert project_1_response.status_code == 200
    project_1_id = project_1_response.json()["id"]

    project_2_response = client.post(
        "/projects/",
        headers=user_2,
        json={
            "name": "Projeto Global Bob",
            "project_type": "PECAS",
            "responsible_login": "bob",
            "fte": 1.0,
            "planned_start": "2026-06-01T00:00:00",
            "planned_end": "2026-06-10T00:00:00",
            "severity": "Gravíssimo",
            "urgency": "Imediatamente",
            "trend": "Piora rapidamente",
            "objective_clarity": "Objetivo indefinido ou exploratório",
            "method_clarity": "Métodos desconhecidos ou inexistentes",
            "estimated_cost": 200.0,
        },
    )
    assert project_2_response.status_code == 200
    project_2_id = project_2_response.json()["id"]

    for task_name in ["alice-task-1", "alice-task-2"]:
        task_response = client.post(
            f"/projects/{project_1_id}/tasks/",
            headers=user_1,
            json={
                "name": task_name,
                "planned_start": "2026-05-10T00:00:00",
                "planned_end": "2026-05-12T00:00:00",
                "cost": 100.0,
            },
        )
        assert task_response.status_code == 200

    complete_response = client.post(
        f"/projects/{project_1_id}/tasks/alice-task-1/complete",
        headers=user_1,
    )
    assert complete_response.status_code == 200

    dashboard_response = client.get(
        "/dashboard/projects-by-responsible",
        headers=user_1,
    )
    assert dashboard_response.status_code == 200
    payload = dashboard_response.json()
    assert payload["chart"] == "projects_by_responsible"

    items_by_id = {item["project_id"]: item for item in payload["items"]}
    assert project_1_id in items_by_id
    assert project_2_id in items_by_id

    alice_item = items_by_id[project_1_id]
    assert alice_item["project_name"] == "Projeto Global Alice"
    assert alice_item["project_type"] == "LAYOUT"
    assert alice_item["project_type_label"] == "LAYOUT"
    assert alice_item["responsible_login"] == "alice"
    assert alice_item["estimated_cost"] == 1500.0
    assert alice_item["task_count"] == 2
    assert alice_item["completed_task_count"] == 1
    assert alice_item["percent_completed"] == 50.0
    assert alice_item["priority_level"] == 5
    assert alice_item["priority_label"] == "Prioridade 5"
    assert alice_item["complexity_score"] == 3
    assert alice_item["complexity_label"] == "Complexidade 3"
    assert alice_item["year"] == 2026
    assert alice_item["month"] == 5
    assert alice_item["month_label"] == "MAI"
    assert alice_item["period_label"] == "MAI 2026"

    bob_item = items_by_id[project_2_id]
    assert bob_item["project_name"] == "Projeto Global Bob"
    assert bob_item["project_type"] == "PECAS"
    assert bob_item["responsible_login"] == "bob"
    assert bob_item["task_count"] == 0
    assert bob_item["completed_task_count"] == 0
    assert bob_item["percent_completed"] == 0.0
    assert bob_item["gut_score"] == 125
    assert bob_item["priority_level"] == 1
    assert bob_item["priority_label"] == "Prioridade 1"
    assert bob_item["complexity_score"] == 5
    assert bob_item["complexity_label"] == "Complexidade 5"
    assert bob_item["year"] == 2026
    assert bob_item["month"] == 6

    second_user_dashboard_response = client.get(
        "/dashboard/projects-by-responsible",
        headers=user_2,
    )
    assert second_user_dashboard_response.status_code == 200
    second_user_ids = {
        item["project_id"]
        for item in second_user_dashboard_response.json()["items"]
    }
    assert {project_1_id, project_2_id}.issubset(second_user_ids)

    user_1_projects = client.get("/projects/", headers=user_1)
    assert user_1_projects.status_code == 200
    user_1_project_ids = {project["id"] for project in user_1_projects.json()}
    assert project_1_id in user_1_project_ids
    assert project_2_id not in user_1_project_ids


def test_dashboard_keeps_small_non_zero_type_values(client, monkeypatch):
    auth = {"Authorization": "Bearer user-1"}

    mapping_project = _create_project_and_task(
        client,
        auth,
        project_name="Projeto Mapeamento",
        project_type="MAPEAMENTO",
        task_name="task-map",
    )
    tiny_project = _create_project_and_task(
        client,
        auth,
        project_name="Projeto Normatizacao",
        project_type="NORMATIZACAO",
        task_name="task-norm",
    )

    _patch_utcnow(
        monkeypatch,
        [
            datetime(2026, 1, 1, 8, 0, 0),
            datetime(2026, 1, 14, 3, 27, 44),  # 307:27:44
            datetime(2026, 1, 20, 9, 0, 0),
            datetime(2026, 1, 20, 9, 2, 7),    # 00:02:07
        ],
    )

    assert client.post(f"/projects/{mapping_project}/tasks/task-map/start", headers=auth).status_code == 200
    assert client.post(f"/projects/{mapping_project}/tasks/task-map/stop", headers=auth).status_code == 200
    assert client.post(f"/projects/{tiny_project}/tasks/task-norm/start", headers=auth).status_code == 200
    assert client.post(f"/projects/{tiny_project}/tasks/task-norm/stop", headers=auth).status_code == 200

    response = client.get("/dashboard/avg-real-days-by-project-type", headers=auth)
    assert response.status_code == 200
    payload = response.json()

    types = {item["project_type"] for item in payload["items"]}
    assert "MAPEAMENTO" in types
    assert "NORMATIZACAO" in types

    mapping_item = next(item for item in payload["items"] if item["project_type"] == "MAPEAMENTO")
    tiny_item = next(item for item in payload["items"] if item["project_type"] == "NORMATIZACAO")

    assert round(mapping_item["average_days"], 4) == 12.8109
    assert 0 < tiny_item["average_days"] < 0.01


def test_dashboard_returns_planned_vs_real_days_by_type(client, monkeypatch):
    auth = {"Authorization": "Bearer user-1"}

    project_1 = _create_project_and_task(
        client,
        auth,
        project_name="Projeto Layout 1",
        project_type="LAYOUT",
        task_name="task-layout-1",
    )
    project_2 = _create_project_and_task(
        client,
        auth,
        project_name="Projeto Layout 2",
        project_type="LAYOUT",
        task_name="task-layout-2",
    )

    _patch_utcnow(
        monkeypatch,
        [
            datetime(2026, 1, 1, 8, 0, 0),
            datetime(2026, 1, 3, 8, 0, 0),  # 2 dias
            datetime(2026, 1, 4, 8, 0, 0),
            datetime(2026, 1, 8, 8, 0, 0),  # 4 dias
        ],
    )

    assert client.post(f"/projects/{project_1}/tasks/task-layout-1/start", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_1}/tasks/task-layout-1/stop", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_2}/tasks/task-layout-2/start", headers=auth).status_code == 200
    assert client.post(f"/projects/{project_2}/tasks/task-layout-2/stop", headers=auth).status_code == 200

    response = client.get("/dashboard/avg-planned-vs-real-days-by-project-type", headers=auth)
    assert response.status_code == 200
    payload = response.json()

    assert payload["chart"] == "avg_planned_vs_real_days_by_project_type"
    layout_item = next(item for item in payload["items"] if item["project_type"] == "LAYOUT")
    assert round(layout_item["real_average_days"], 4) == 3.0
    assert layout_item["planned_average_days"] > 0
