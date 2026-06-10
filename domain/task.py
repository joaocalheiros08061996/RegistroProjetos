"""Entidade de tarefa de projeto e suas regras de tempo/status."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from .enums import TaskStatus
from .exceptions import (
    TaskAlreadyCompletedError,
    TaskAlreadyStartedError,
    TaskNotStartedError,
    ValidationError,
)
from .time_entry import TimeEntry
from .validation import TASK_DESCRIPTION_MAX_LENGTH


class Task:
    """Modela uma tarefa, incluindo planejamento, status e apontamentos de tempo."""

    def __init__(
        self,
        name: str,
        planned_start: datetime,
        planned_end: datetime,
        cost: float = 0.0,
        description: str = "",
    ):
        """Cria uma tarefa planejada validando nome, descrição e intervalo planejado."""
        if not name or not name.strip():
            raise ValidationError("Nome da tarefa obrigatorio.")
        if planned_end < planned_start:
            raise ValidationError("Data final planejada anterior a inicial.")
        normalized_description = str(description or "").strip()
        if len(normalized_description) > TASK_DESCRIPTION_MAX_LENGTH:
            raise ValidationError("Descricao da tarefa excede o tamanho permitido.")

        self._id: Optional[int] = None
        self._name: str = name.strip()
        self._description: str = normalized_description
        self._planned_start: datetime = planned_start
        self._planned_end: datetime = planned_end
        self.cost: float = float(cost)

        self._status: TaskStatus = TaskStatus.PLANNED
        self._time_entries: List[TimeEntry] = []
        self._current_entry: Optional[TimeEntry] = None

    # ---------- Identidade ----------

    @property
    def id(self) -> Optional[int]:
        """Retorna o identificador persistido da tarefa, quando existir."""
        return self._id

    def _set_id(self, id_value: int) -> None:
        """Define o ID durante hidratação/persistência sem permitir sobrescrita."""
        if self._id is not None:
            raise ValidationError("Id ja definido.")
        self._id = int(id_value)

    # ---------- Hidratação (repositórios) ----------

    def _set_status(self, status: TaskStatus | str) -> None:
        """Restaura o status persistido e ajusta a entrada corrente se necessário."""
        self._status = TaskStatus(status)
        if self._status != TaskStatus.IN_PROGRESS:
            self._current_entry = None

    def _add_time_entry(self, entry: TimeEntry) -> None:
        """Adiciona entrada persistida e reabre a tarefa se a entrada ainda estiver aberta."""
        self._time_entries.append(entry)
        if entry.end is None:
            self._current_entry = entry
            self._status = TaskStatus.IN_PROGRESS

    # ---------- Propriedades ----------

    @property
    def name(self) -> str:
        """Retorna o nome normalizado da tarefa."""
        return self._name

    @property
    def description(self) -> str:
        """Retorna a descrição normalizada da tarefa."""
        return self._description

    @property
    def planned_start(self) -> datetime:
        """Retorna a data/hora planejada de início."""
        return self._planned_start

    @property
    def planned_end(self) -> datetime:
        """Retorna a data/hora planejada de término."""
        return self._planned_end

    @property
    def status(self) -> TaskStatus:
        """Retorna o status semântico atual da tarefa."""
        return self._status

    # ---------- Controle de tempo ----------

    def start(self, when: Optional[datetime] = None) -> None:
        """Inicia uma nova entrada de tempo respeitando regras de status."""
        if self._status == TaskStatus.COMPLETED:
            raise TaskAlreadyCompletedError("Tarefa ja concluida.")
        if self._current_entry is not None:
            raise TaskAlreadyStartedError("Tarefa ja iniciada.")

        now = when or datetime.utcnow()
        entry = TimeEntry(start=now)
        self._time_entries.append(entry)
        self._current_entry = entry
        self._status = TaskStatus.IN_PROGRESS

    def stop(self, when: Optional[datetime] = None) -> timedelta:
        """Encerra a entrada aberta e retorna a duração registrada."""
        if self._current_entry is None:
            raise TaskNotStartedError("Nenhuma entrada em andamento para parar.")

        now = when or datetime.utcnow()
        self._current_entry.stop(now)
        duration = self._current_entry.duration
        self._current_entry = None

        if self._status != TaskStatus.COMPLETED:
            self._status = TaskStatus.PAUSED

        return duration

    def add_manual_entry(self, start: datetime, end: datetime) -> None:
        """Registra manualmente uma entrada já encerrada."""
        if end < start:
            raise ValidationError("End < start em add_manual_entry.")
        entry = TimeEntry(start=start)
        entry.stop(end)
        self._time_entries.append(entry)

    # ---------- Métricas de tempo ----------

    @property
    def time_entries(self) -> List[TimeEntry]:
        """Retorna uma cópia das entradas de tempo da tarefa."""
        return list(self._time_entries)

    @property
    def actual_time(self) -> timedelta:
        """Soma as durações reais de todas as entradas de tempo."""
        total = timedelta()
        for te in self._time_entries:
            total += te.duration
        return total

    @property
    def planned_duration(self) -> timedelta:
        """Calcula a duração planejada da tarefa."""
        return self._planned_end - self._planned_start

    # ---------- Progresso (SEMÂNTICO) ----------

    @property
    def is_completed(self) -> bool:
        """Indica se a tarefa está concluída."""
        return self._status == TaskStatus.COMPLETED

    @property
    def percent_completed(self) -> float:
        """Retorna progresso semântico baseado exclusivamente no status."""
        return 100.0 if self.is_completed else 0.0

    def mark_completed(self) -> None:
        """Marca a tarefa como concluída, encerrando medição aberta se houver."""
        if self._status == TaskStatus.COMPLETED:
            raise TaskAlreadyCompletedError("Tarefa ja esta concluida.")
        if self._current_entry is not None:
            self.stop()
        self._status = TaskStatus.COMPLETED
