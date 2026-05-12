from fastapi import APIRouter, Depends

from api.deps import AuthenticatedUser, get_current_user, get_routine_activity_service
from api.dtos import RoutineActivityResponseDTO, StartRoutineActivityDTO
from application.services import RoutineActivityService

router = APIRouter(
    prefix="/routine-activities",
    tags=["Routine Activities"],
)


def to_routine_response(activity) -> RoutineActivityResponseDTO:
    return RoutineActivityResponseDTO(
        id=activity.id,
        tipo_atividade=activity.tipo_atividade,
        responsavel=activity.responsavel,
        descricao=activity.descricao,
        inicio=activity.inicio,
        fim=activity.fim,
        ano=activity.ano,
        mes=activity.mes,
        dia=activity.dia,
        horas_trabalhadas=activity.horas_trabalhadas,
    )


@router.post("/start", response_model=RoutineActivityResponseDTO)
def start_routine_activity(
    dto: StartRoutineActivityDTO,
    service: RoutineActivityService = Depends(get_routine_activity_service),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    activity = service.start_activity(
        user_id=current_user.id,
        tipo_atividade=dto.tipo_atividade,
        responsavel=dto.responsavel,
        descricao=dto.descricao,
    )
    return to_routine_response(activity)


@router.get("/current", response_model=RoutineActivityResponseDTO | None)
def get_current_routine_activity(
    service: RoutineActivityService = Depends(get_routine_activity_service),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    activity = service.get_current_activity(current_user.id)
    if activity is None:
        return None
    return to_routine_response(activity)


@router.post("/finish-current", response_model=RoutineActivityResponseDTO)
def finish_current_routine_activity(
    service: RoutineActivityService = Depends(get_routine_activity_service),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    activity = service.finish_current_activity(current_user.id)
    return to_routine_response(activity)
