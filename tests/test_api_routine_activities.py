AUTH_HEADER = {"Authorization": "Bearer test-user-123"}


def test_start_routine_activity_api(client):
    response = client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={
            "tipo_atividade": "Análise de Processos",
            "responsavel": "João Calheiros",
            "descricao": "Mapeando fluxos.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert body["tipo_atividade"] == "Análise de Processos"
    assert body["responsavel"] == "João Calheiros"
    assert "user_email" not in body
    assert body["fim"] is None


def test_start_second_open_routine_activity_returns_422(client):
    first = client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={"tipo_atividade": "Cadastro", "descricao": ""},
    )
    assert first.status_code == 200

    second = client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={"tipo_atividade": "Atualização de Custos", "descricao": ""},
    )
    assert second.status_code == 422


def test_get_current_routine_activity(client):
    client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={"tipo_atividade": "Reuniões", "descricao": "Daily"},
    )

    response = client.get("/routine-activities/current", headers=AUTH_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["tipo_atividade"] == "Reuniões"
    assert body["fim"] is None


def test_finish_current_routine_activity(client):
    start_response = client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={"tipo_atividade": "Finame", "descricao": ""},
    )
    assert start_response.status_code == 200

    finish_response = client.post(
        "/routine-activities/finish-current",
        headers=AUTH_HEADER,
    )
    assert finish_response.status_code == 200

    finished = finish_response.json()
    assert finished["fim"] is not None
    assert finished["horas_trabalhadas"] is not None
    assert finished["horas_trabalhadas"] >= 0


def test_get_current_after_finish_returns_null(client):
    client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={"tipo_atividade": "Análise de Processos", "descricao": ""},
    )
    client.post("/routine-activities/finish-current", headers=AUTH_HEADER)

    current_response = client.get("/routine-activities/current", headers=AUTH_HEADER)
    assert current_response.status_code == 200
    assert current_response.json() is None


def test_routine_activities_are_user_scoped(client):
    user_1_header = {"Authorization": "Bearer user-1"}
    user_2_header = {"Authorization": "Bearer user-2"}

    start_user_1 = client.post(
        "/routine-activities/start",
        headers=user_1_header,
        json={"tipo_atividade": "Atendimento de Fábrica", "descricao": "Atividade U1"},
    )
    assert start_user_1.status_code == 200

    current_user_2 = client.get("/routine-activities/current", headers=user_2_header)
    assert current_user_2.status_code == 200
    assert current_user_2.json() is None

    start_user_2 = client.post(
        "/routine-activities/start",
        headers=user_2_header,
        json={"tipo_atividade": "Cadastro", "descricao": "Atividade U2"},
    )
    assert start_user_2.status_code == 200


def test_start_routine_activity_accepts_all_allowed_types(client):
    allowed_types = [
        "Atendimento de Fábrica",
        "Cadastro",
        "Atualização de Custos",
        "Finame",
        "Reuniões",
        "Análise de Processos",
    ]

    for activity_type in allowed_types:
        start_response = client.post(
            "/routine-activities/start",
            headers=AUTH_HEADER,
            json={"tipo_atividade": activity_type, "descricao": ""},
        )
        assert start_response.status_code == 200

        finish_response = client.post(
            "/routine-activities/finish-current",
            headers=AUTH_HEADER,
        )
        assert finish_response.status_code == 200


def test_start_routine_activity_with_removed_type_returns_422(client):
    response = client.post(
        "/routine-activities/start",
        headers=AUTH_HEADER,
        json={"tipo_atividade": "Documentação", "descricao": ""},
    )

    assert response.status_code == 422


def test_routine_activity_requires_authentication(client):
    start_response = client.post(
        "/routine-activities/start",
        json={"tipo_atividade": "Cadastro", "descricao": ""},
    )
    assert start_response.status_code == 401

    current_response = client.get("/routine-activities/current")
    assert current_response.status_code == 401

    finish_response = client.post("/routine-activities/finish-current")
    assert finish_response.status_code == 401
