"""Fachada de compatibilidade para importação das entidades principais."""

from .project import Project
from .task import Task
from .time_entry import TimeEntry

__all__ = [
    "Project",
    "Task",
    "TimeEntry",
]
