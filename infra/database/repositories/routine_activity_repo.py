from datetime import datetime
from typing import Optional

from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor

from domain.exceptions import ValidationError
from domain.repositories import IRoutineActivityRepository
from domain.routine_activity import RoutineActivity
from infra.database.connection import get_connection


class SupabaseRoutineActivityRepository(IRoutineActivityRepository):
    def save(self, activity: RoutineActivity) -> int:
        try:
            with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    insert into atividades (
                        user_id,
                        tipo_atividade,
                        descricao,
                        inicio,
                        fim,
                        ano,
                        mes,
                        dia,
                        horas_trabalhadas
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    returning *
                    """,
                    (
                        activity.user_id,
                        activity.tipo_atividade,
                        activity.descricao,
                        activity.inicio,
                        activity.fim,
                        activity.ano,
                        activity.mes,
                        activity.dia,
                        activity.horas_trabalhadas,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
        except IntegrityError as exc:
            if getattr(exc, "pgcode", None) == "23505":
                raise ValidationError("Ja existe uma atividade em andamento para este usuario.") from exc
            raise

        if not row:
            raise RuntimeError("Falha ao persistir atividade de rotina.")

        if activity.id is None:
            activity._set_id(row["id"])

        return activity.id or row["id"]

    def get_current(self, user_id: str) -> Optional[RoutineActivity]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select *
                from atividades
                where user_id = %s
                  and fim is null
                order by id desc
                limit 1
                """,
                (user_id,),
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._build_activity(row)

    def finish_current(
        self,
        user_id: str,
        finished_at: datetime,
        hours: float,
    ) -> Optional[RoutineActivity]:
        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                update atividades
                set fim = %s, horas_trabalhadas = %s
                where id = (
                    select id
                    from atividades
                    where user_id = %s and fim is null
                    order by id desc
                    limit 1
                )
                returning *
                """,
                (finished_at, hours, user_id),
            )
            row = cur.fetchone()
            conn.commit()

        if not row:
            return None

        return self._build_activity(row)

    @staticmethod
    def _build_activity(row: dict) -> RoutineActivity:
        activity = RoutineActivity(
            user_id=row["user_id"],
            tipo_atividade=row["tipo_atividade"],
            descricao=row.get("descricao") or "",
            inicio=row["inicio"],
            fim=row.get("fim"),
            horas_trabalhadas=row.get("horas_trabalhadas"),
            ano=row.get("ano"),
            mes=row.get("mes"),
            dia=row.get("dia"),
        )
        activity._set_id(row["id"])
        return activity
