from fastapi import APIRouter, Depends

from api.deps import get_current_user_id, get_routine_activity_service
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
    user_id: str = Depends(get_current_user_id),
):
    activity = service.start_activity(
        user_id=user_id,
        tipo_atividade=dto.tipo_atividade,
        descricao=dto.descricao,
    )
    return to_routine_response(activity)


@router.get("/current", response_model=RoutineActivityResponseDTO | None)
def get_current_routine_activity(
    service: RoutineActivityService = Depends(get_routine_activity_service),
    user_id: str = Depends(get_current_user_id),
):
    activity = service.get_current_activity(user_id)
    if activity is None:
        return None
    return to_routine_response(activity)


@router.post("/finish-current", response_model=RoutineActivityResponseDTO)
def finish_current_routine_activity(
    service: RoutineActivityService = Depends(get_routine_activity_service),
    user_id: str = Depends(get_current_user_id),
):
    activity = service.finish_current_activity(user_id)
    return to_routine_response(activity)
