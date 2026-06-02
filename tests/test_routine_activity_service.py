from application.services import RoutineActivityService
from domain.exceptions import ValidationError
from infra.in_memory_repos import InMemoryRoutineActivityRepository


def build_service() -> RoutineActivityService:
    repo = InMemoryRoutineActivityRepository()
    return RoutineActivityService(repo)


def test_start_activity_creates_open_record():
    service = build_service()

    created = service.start_activity(
        user_id="user-1",
        tipo_atividade="Análise de Processos",
        responsavel="JACKSON",
        descricao="Mapear processo atual",
    )

    assert created.id is not None
    assert created.responsavel == "Jackson"
    assert created.fim is None
    assert created.tipo_atividade == "Análise de Processos"


def test_start_activity_rejects_second_open_record():
    service = build_service()
    service.start_activity(user_id="user-1", tipo_atividade="Cadastro")

    try:
        service.start_activity(user_id="user-1", tipo_atividade="Atualização de Custos")
        assert False, "Era esperado ValidationError"
    except ValidationError as exc:
        assert "atividade em andamento" in str(exc)


def test_get_current_activity_returns_user_scoped_activity():
    service = build_service()
    service.start_activity(user_id="user-1", tipo_atividade="Atendimento de Fábrica")

    current_user_1 = service.get_current_activity("user-1")
    current_user_2 = service.get_current_activity("user-2")

    assert current_user_1 is not None
    assert current_user_1.tipo_atividade == "Atendimento de Fábrica"
    assert current_user_2 is None


def test_finish_current_activity_sets_end_and_hours():
    service = build_service()
    service.start_activity(user_id="user-1", tipo_atividade="Finame")

    finished = service.finish_current_activity("user-1")

    assert finished.fim is not None
    assert finished.horas_trabalhadas is not None
    assert finished.horas_trabalhadas >= 0
    assert service.get_current_activity("user-1") is None


def test_finish_current_activity_without_open_record_raises():
    service = build_service()

    try:
        service.finish_current_activity("user-1")
        assert False, "Era esperado ValidationError"
    except ValidationError as exc:
        assert "Nao ha atividade em andamento" in str(exc)


def test_start_activity_rejects_removed_type():
    service = build_service()

    try:
        service.start_activity(user_id="user-1", tipo_atividade="Documentação")
        assert False, "Era esperado ValidationError"
    except ValidationError as exc:
        assert "Tipo de atividade invalido" in str(exc)
