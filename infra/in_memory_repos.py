from datetime import datetime
from typing import Dict, List, Optional

from domain.entities import Project, Task, TimeEntry
from domain.enums import TaskStatus
from domain.repositories import IProjectRepository, ITaskRepository


class InMemoryProjectRepository(IProjectRepository):
    def __init__(self):
        self._storage: Dict[int, Project] = {}
        self._next_id = 1

    def save(self, project: Project) -> int:
        if project.id is None:
            project._set_id(self._next_id)
            self._next_id += 1
        self._storage[project.id] = project
        return project.id

    def find_by_id(self, project_id: int, user_id: str) -> Optional[Project]:
        project = self._storage.get(project_id)
        if project and project.user_id == user_id:
            return project
        return None

    def list_by_user(self, user_id: str) -> List[Project]:
        return [
            project
            for project in self._storage.values()
            if project.user_id == user_id
        ]

    def delete(self, project_id: int, user_id: str) -> bool:
        project = self._storage.get(project_id)
        if not project or project.user_id != user_id:
            return False
        del self._storage[project_id]
        return True


class InMemoryTaskRepository(ITaskRepository):
    def __init__(self):
        self._storage: Dict[int, Dict[int, Task]] = {}
        self._project_owners: Dict[int, str] = {}
        self._next_id = 1

    def save(self, task: Task, project_id: int, user_id: str) -> int:
        if project_id not in self._storage:
            self._storage[project_id] = {}
            self._project_owners[project_id] = user_id

        if task.id is None:
            task._set_id(self._next_id)
            self._next_id += 1

        self._storage[project_id][task.id] = task
        return task.id

    def find_by_id(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
    ) -> Optional[Task]:
        owner = self._project_owners.get(project_id)
        if owner is not None and owner != user_id:
            return None
        return self._storage.get(project_id, {}).get(task_id)

    def delete_by_name(self, project_id: int, user_id: str, task_name: str) -> bool:
        owner = self._project_owners.get(project_id)
        if owner is not None and owner != user_id:
            return False

        tasks = self._storage.get(project_id, {})
        task_id_to_remove = next(
            (task_id for task_id, task in tasks.items() if task.name == task_name),
            None,
        )
        if task_id_to_remove is None:
            return False

        del tasks[task_id_to_remove]
        if not tasks:
            self._storage.pop(project_id, None)
            self._project_owners.pop(project_id, None)
        return True

    def delete_by_project(self, project_id: int, user_id: str) -> int:
        owner = self._project_owners.get(project_id)
        if owner is not None and owner != user_id:
            return 0

        tasks = self._storage.pop(project_id, {})
        self._project_owners.pop(project_id, None)
        return len(tasks)

    def append_time_entry(
        self,
        task_id: int,
        project_id: int,
        user_id: str,
        entry: TimeEntry,
    ) -> None:
        task = self.find_by_id(task_id, project_id, user_id)
        if not task:
            raise ValueError("Task not found")
        task._add_time_entry(entry)

    def update_status(self, task_id: int, status: str) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        task._set_status(TaskStatus(status))

    def start_time_entry(self, task_id: int, start: datetime) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        # In-memory repo persiste apenas; regra de dominio ja foi aplicada no service.
        # Mantemos no-op para evitar aplicar transicao de estado duas vezes.
        return None

    def close_open_time_entry(self, task_id: int, end: datetime) -> None:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        # Sem entrada aberta, o comportamento persistente esperado e no-op.
        return None

    def list_time_entries(self, task_id: int) -> list[tuple]:
        task = self._find_task(task_id)
        if not task:
            raise ValueError("Task not found")
        return [(e.start, e.end) for e in task.time_entries]

    def _find_task(self, task_id: int) -> Optional[Task]:
        for tasks in self._storage.values():
            if task_id in tasks:
                return tasks[task_id]
        return None
