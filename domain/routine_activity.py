from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from domain.exceptions import ValidationError


ROUTINE_ACTIVITY_TYPES: Sequence[str] = (
    "Atendimento de Fábrica",
    "Cadastro",
    "Atualização de Custos",
    "Finame",
    "Reuniões",
    "Análise de Processos",
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class RoutineActivity:
    def __init__(
        self,
        *,
        user_id: str,
        tipo_atividade: str,
        descricao: str = "",
        inicio: Optional[datetime] = None,
        fim: Optional[datetime] = None,
        horas_trabalhadas: Optional[float] = None,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        dia: Optional[int] = None,
    ):
        if not user_id or not user_id.strip():
            raise ValidationError("User ID da atividade e obrigatorio.")

        tipo = str(tipo_atividade).strip()
        if tipo not in ROUTINE_ACTIVITY_TYPES:
            raise ValidationError("Tipo de atividade invalido.")

        started_at = _as_utc(inicio or datetime.now(timezone.utc))
        finished_at = _as_utc(fim) if fim is not None else None

        if finished_at is not None and finished_at < started_at:
            raise ValidationError("Fim da atividade nao pode ser anterior ao inicio.")

        self._id: Optional[int] = None
        self.user_id = user_id.strip()
        self.tipo_atividade = tipo
        self.descricao = (descricao or "").strip()
        self.inicio = started_at
        self.fim = finished_at
        self.horas_trabalhadas = horas_trabalhadas
        self.ano = int(ano) if ano is not None else started_at.year
        self.mes = int(mes) if mes is not None else started_at.month
        self.dia = int(dia) if dia is not None else started_at.day

    @property
    def id(self) -> Optional[int]:
        return self._id

    def _set_id(self, value: int) -> None:
        if self._id is not None:
            raise ValidationError("Id da atividade ja definido.")
        self._id = int(value)

    @property
    def is_active(self) -> bool:
        return self.fim is None

    def finalize(self, when: Optional[datetime] = None) -> None:
        if self.fim is not None:
            raise ValidationError("Atividade ja finalizada.")

        finished_at = _as_utc(when or datetime.now(timezone.utc))
        if finished_at < self.inicio:
            raise ValidationError("Fim da atividade nao pode ser anterior ao inicio.")

        self.fim = finished_at
        hours = (self.fim - self.inicio).total_seconds() / 3600
        self.horas_trabalhadas = round(hours, 10)
