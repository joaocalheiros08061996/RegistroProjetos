# tests/integration/supabase/test_task_supabase.py

import os
import pytest
from datetime import datetime, timedelta

from domain.entities import Task
from domain.enums import TaskStatus
from infra.database.repositories.project_repo import SupabaseProjectRepository
from infra.database.repositories.task_repo import SupabaseTaskRepository
from tests.integration.supabase.helpers import create_project_for_test

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="Defina RUN_INTEGRATION_TESTS=1 para executar testes de integracao.",
    ),
]

def test_supabase_can_save_task_with_real_project():
    user_id = "00000000-0000-0000-0000-000000000001"

    project_repo = SupabaseProjectRepository()
    task_repo = SupabaseTaskRepository()

    # 1️⃣ cria project real (FK)
    project = create_project_for_test(project_repo, user_id)

    # 2️⃣ cria task em memória (domain já testado)
    task = Task(
        name="Task Supabase Test",
        planned_start=datetime.utcnow(),
        planned_end=datetime.utcnow() + timedelta(days=2),
        cost=100.0,
    )

    # 3️⃣ salva no Supabase
    task_id = task_repo.save(
        task=task,
        project_id=project.id,
        user_id=user_id,
    )

    # 4️⃣ asserts mínimos
    assert task_id is not None
    assert task.id == task_id
