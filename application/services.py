from datetime import datetime

import application.task_service as task_service_module
import application.routine_activity_service as routine_activity_service_module
from application.dashboard_service import DashboardService
from application.project_service import ProjectService
from application.routine_activity_service import RoutineActivityService as _RoutineActivityService
from application.task_service import TaskService as _TaskService


class RoutineActivityService(_RoutineActivityService):
    """
    Compatibilidade para callers que ainda monkeypatcham
    `application.services.datetime`.
    """

    def _sync_datetime_compat(self) -> None:
        routine_activity_service_module.datetime = datetime

    def start_activity(self, **kwargs):
        self._sync_datetime_compat()
        return super().start_activity(**kwargs)

    def finish_current_activity(self, user_id: str):
        self._sync_datetime_compat()
        return super().finish_current_activity(user_id)


class TaskService(_TaskService):
    """
    Compatibilidade para callers que ainda monkeypatcham
    `application.services.datetime`.
    """

    def _sync_datetime_compat(self) -> None:
        task_service_module.datetime = datetime

    def start_task(self, project_id: int, user_id: str, task_name: str) -> None:
        self._sync_datetime_compat()
        return super().start_task(project_id, user_id, task_name)

    def stop_task(self, project_id: int, user_id: str, task_name: str) -> float:
        self._sync_datetime_compat()
        return super().stop_task(project_id, user_id, task_name)

    def complete_task(self, project_id: int, user_id: str, task_name: str) -> None:
        self._sync_datetime_compat()
        return super().complete_task(project_id, user_id, task_name)

__all__ = [
    "DashboardService",
    "ProjectService",
    "RoutineActivityService",
    "TaskService",
]
