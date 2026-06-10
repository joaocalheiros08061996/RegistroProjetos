from datetime import datetime, timezone
from typing import Optional

from domain.exceptions import ValidationError
from domain.repositories import IRoutineActivityRepository
from domain.routine_activity import RoutineActivity


class RoutineActivityService:
    def __init__(self, routine_repo: IRoutineActivityRepository):
        self.routine_repo = routine_repo

    def start_activity(
        self,
        *,
        user_id: str,
        tipo_atividade: str,
        responsavel: str = "",
        descricao: str = "",
    ) -> RoutineActivity:
        current = self.routine_repo.get_current(user_id)
        if current is not None:
            raise ValidationError("Ja existe uma atividade em andamento para este usuario.")

        activity = RoutineActivity(
            user_id=user_id,
            tipo_atividade=tipo_atividade,
            responsavel=responsavel,
            descricao=descricao,
        )
        self.routine_repo.save(activity)
        return activity

    def get_current_activity(self, user_id: str) -> Optional[RoutineActivity]:
        return self.routine_repo.get_current(user_id)

    def finish_current_activity(self, user_id: str) -> RoutineActivity:
        current = self.routine_repo.get_current(user_id)
        if current is None:
            raise ValidationError("Nao ha atividade em andamento para finalizar.")

        finished_at = datetime.now(timezone.utc)
        if finished_at < current.inicio:
            raise ValidationError("Fim da atividade nao pode ser anterior ao inicio.")

        hours = round((finished_at - current.inicio).total_seconds() / 3600, 10)

        finished = self.routine_repo.finish_current(
            user_id=user_id,
            finished_at=finished_at,
            hours=hours,
        )
        if finished is None:
            raise ValidationError("Nao ha atividade em andamento para finalizar.")
        return finished
