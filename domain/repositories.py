from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from .entities import Project, Task, TimeEntry
from .routine_activity import RoutineActivity


class IProjectRepository(ABC):
    @abstractmethod
    def save(self, project: Project) -> int:
        """Persiste um projeto pertencente a um usuário."""

    @abstractmethod
    def find_by_id(self, project_id: int, user_id: str) -> Optional[Project]:
        """Retorna o projeto se pertencer ao usuário."""

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Project]:
        """Lista todos os projetos de um usuário."""

    @abstractmethod
    def delete(self, project_id: int, user_id: str) -> bool:
        """Remove um projeto do usuário. Retorna se houve exclusão."""


class ITaskRepository(ABC):
    @abstractmethod
    def save(self, task: Task, project_id: int, user_id: str) -> int:
        """Persiste uma task associada a um projeto do usuário."""

    @abstractmethod
    def find_by_id(
        self, task_id: int, project_id: int, user_id: str
    ) -> Optional[Task]:
        """Retorna a task se pertencer ao projeto e ao usuário."""

    @abstractmethod
    def delete_by_name(self, project_id: int, user_id: str, task_name: str) -> bool:
        """Remove uma task por nome dentro do projeto do usuário."""

    @abstractmethod
    def delete_by_project(self, project_id: int, user_id: str) -> int:
        """Remove todas as tasks de um projeto do usuário."""

    @abstractmethod
    def append_time_entry(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
        entry: TimeEntry,
    ) -> None:
        """
        Persiste uma entrada de tempo associada a uma task.
        Não altera status nem regras de negócio.
        """

    @abstractmethod
    def update_status(self, task_id: int, status: str) -> None:
        """
        Persiste o novo status de uma task.
        A decisão de mudança de status é responsabilidade do domínio.
        """

    @abstractmethod
    def start_time_entry(self, task_id: int, start: datetime) -> None:
        """
        Persiste o início de uma medição de tempo.
        Não decide se a task pode ou não ser iniciada.
        """

    @abstractmethod
    def close_open_time_entry(self, task_id: int, end: datetime) -> None:
        """
        Persiste o encerramento da última entrada de tempo em aberto.
        Não valida regras de domínio.
        """

    @abstractmethod
    def list_time_entries(self, task_id: int) -> list[tuple]:
        """Lista as entradas de tempo (start, end) de uma task."""


class IRoutineActivityRepository(ABC):
    @abstractmethod
    def save(self, activity: RoutineActivity) -> int:
        """Persiste uma nova atividade de rotina."""

    @abstractmethod
    def get_current(self, user_id: str) -> Optional[RoutineActivity]:
        """Retorna atividade em andamento do usuario, se existir."""

    @abstractmethod
    def finish_current(
        self,
        user_id: str,
        finished_at: datetime,
        hours: float,
    ) -> Optional[RoutineActivity]:
        """Finaliza a atividade em andamento e retorna o registro atualizado."""


class IDashboardRepository(ABC):
    @abstractmethod
    def list_avg_real_days_by_project_type(self) -> list[dict]:
        """
        Retorna média global de dias reais por tipo de projeto.
        Cada item deve conter:
        - project_type (str)
        - average_days (float)
        """

    @abstractmethod
    def list_avg_planned_vs_real_days_by_project_type(self) -> list[dict]:
        """
        Retorna média global de dias planejados vs reais por tipo de projeto.
        Cada item deve conter:
        - project_type (str)
        - planned_average_days (float)
        - real_average_days (float)
        """

    @abstractmethod
    def list_routine_total_days_by_month(self) -> list[dict]:
        """
        Retorna dias totais globais de atividades de rotina por tipo, ano e mes.
        Cada item deve conter:
        - user_id (str)
        - activity_type (str)
        - year (int)
        - month (int)
        - total_days (float)
        """

    @abstractmethod
    def list_project_monthly_kpis(self) -> list[dict]:
        """
        Retorna KPIs mensais globais de projetos por tipo, responsavel, ano e mes.
        Cada item deve conter os campos agregados usados pelo dashboard mensal.
        """

    @abstractmethod
    def list_project_complexity_counts(self) -> list[dict]:
        """
        Retorna contagem global de projetos por tipo e score de complexidade.
        Cada item deve conter:
        - project_type (str)
        - complexity_score (int)
        - project_count (int)
        """

    @abstractmethod
    def list_project_complexity_counts_by_month(self) -> list[dict]:
        """
        Retorna contagem global de projetos por mes/ano e score de complexidade.
        Cada item deve conter:
        - project_type (str)
        - responsible_login (str)
        - year (int)
        - month (int)
        - complexity_score (int)
        - project_count (int)
        """

    @abstractmethod
    def list_project_earned_value(self) -> list[dict]:
        """
        Retorna dados de valor agregado por projeto.
        Cada item deve conter:
        - project_id (int)
        - project_name (str)
        - project_type (str)
        - responsible_login (str)
        - year (int)
        - month (int)
        - estimated_cost (float)
        - planned_value (float)
        - earned_value (float)
        - total_task_cost (float)
        - task_count (int)
        - completed_task_count (int)
        """

    @abstractmethod
    def list_project_effort_deviation(self) -> list[dict]:
        """
        Retorna dados de desvio de esforço por tipo, responsavel, ano e mes.
        Cada item deve conter:
        - project_type (str)
        - responsible_login (str)
        - year (int)
        - month (int)
        - task_count (int)
        - planned_effort_hours (float)
        - actual_effort_hours (float)
        """
