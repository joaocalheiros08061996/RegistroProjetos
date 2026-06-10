"""Entidade de intervalo de tempo trabalhado em uma tarefa."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from .exceptions import ValidationError


class TimeEntry:
    """Representa uma medição de tempo com início obrigatório e fim opcional."""

    def __init__(self, start: datetime):
        """Cria uma entrada de tempo ainda aberta a partir de `start`."""
        self.start: datetime = start
        self.end: Optional[datetime] = None

    def _normalize_like_start(self, value: datetime) -> datetime:
        """
        Normaliza `value` para o mesmo "tipo de timezone" de `self.start`.
        - Se `start` for aware, tratamos naive como UTC.
        - Se `start` for naive, convertendo aware para naive em UTC.
        """
        start_is_aware = self.start.tzinfo is not None and self.start.tzinfo.utcoffset(self.start) is not None
        value_is_aware = value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

        if start_is_aware:
            if not value_is_aware:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(self.start.tzinfo)

        if value_is_aware:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def stop(self, end: datetime) -> None:
        """Finaliza a entrada garantindo ordem temporal e timezone compatível."""
        end = self._normalize_like_start(end)
        if self.end is not None:
            raise ValidationError("TimeEntry ja finalizado.")
        if end < self.start:
            raise ValidationError("End < start para TimeEntry.")
        self.end = end

    @property
    def duration(self) -> timedelta:
        """Retorna a duração fechada ou a duração até agora se a entrada estiver aberta."""
        if self.end is None:
            if self.start.tzinfo is not None and self.start.tzinfo.utcoffset(self.start) is not None:
                return datetime.now(tz=self.start.tzinfo) - self.start
            return datetime.utcnow() - self.start
        return self.end - self.start
