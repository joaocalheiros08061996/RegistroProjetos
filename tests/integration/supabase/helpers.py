from datetime import datetime, timedelta
from domain.entities import Project
from domain.enums import ProjectType


def create_project_for_test(project_repo, user_id: str) -> Project:
    project = Project(
        user_id=user_id,
        name="Projeto Teste Task",
        project_type=ProjectType.LAYOUT,
        responsible_login="tester",
        fte=1.0,
        planned_start=datetime.utcnow(),
        planned_end=datetime.utcnow() + timedelta(days=10),
    )

    project_repo.save(project)
    return project