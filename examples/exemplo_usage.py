# exemplo_usage.py
from datetime import datetime
from application.services import ProjectService, TaskService
from infra.in_memory_repos import InMemoryProjectRepository, InMemoryTaskRepository
from domain.enums import ProjectType

proj_repo = InMemoryProjectRepository()
task_repo = InMemoryTaskRepository()

project_service = ProjectService(proj_repo, task_repo)
task_service = TaskService(proj_repo, task_repo)

p = project_service.create_project(
    name="Projeto Demo",
    project_type=ProjectType.LAYOUT,
    responsible_login="user1",
    fte=1.0,
    planned_start=datetime(2026,3,1),
    planned_end=datetime(2026,3,31),
)

task = project_service.add_task_to_project(
    project_id=p.id,
    task_name="Mapeamento",
    planned_start=datetime(2026,3,1),
    planned_end=datetime(2026,3,5),
    cost=1000.0,
)

task_service.start_task(project_id=p.id, task_name="Mapeamento", when=datetime(2026,3,1,9,0))
task_service.stop_task(project_id=p.id, task_name="Mapeamento", when=datetime(2026,3,1,12,0))

print(project_service.get_project_metrics(p.id))
