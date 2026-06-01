from fastapi import APIRouter, Depends, Path

from api.deps import get_current_user_id, get_task_service
from api.dtos import CreateTaskDTO, TaskResponseDTO
from application.services import TaskService
from domain.validation import TASK_NAME_MAX_LENGTH

router = APIRouter(
    prefix="/projects/{project_id}/tasks",
    tags=["Tasks"],
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def to_task_response(task) -> TaskResponseDTO:
    """
    Converte entidade Task do domínio em DTO de resposta.
    """
    return TaskResponseDTO(
        name=task.name,
        status=task.status.value,
        planned_start=task.planned_start,
        planned_end=task.planned_end,
        cost=task.cost,
        actual_seconds=round(task.actual_time.total_seconds(), 2),
        time_entries_count=len(task.time_entries),
        percent_completed=task.percent_completed,
    )


# --------------------------------------------------
# Create Task
# --------------------------------------------------

@router.post("/", response_model=TaskResponseDTO)
def add_task(
    dto: CreateTaskDTO,
    project_id: int = Path(..., gt=0),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Cria uma nova tarefa dentro de um projeto.
    """
    task = service.add_task(
        user_id=user_id,
        project_id=project_id,
        name=dto.name,
        planned_start=dto.planned_start,
        planned_end=dto.planned_end,
        cost=dto.cost,
    )
    return to_task_response(task)


# --------------------------------------------------
# List Tasks
# --------------------------------------------------

@router.get("/", response_model=list[TaskResponseDTO])
def list_tasks(
    project_id: int = Path(..., gt=0),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Lista todas as tarefas de um projeto.
    """
    tasks = service.list_tasks(project_id, user_id)
    return [to_task_response(task) for task in tasks]


# --------------------------------------------------
# Get Task
# --------------------------------------------------

@router.get("/{task_name}", response_model=TaskResponseDTO)
def get_task(
    project_id: int = Path(..., gt=0),
    task_name: str = Path(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Retorna os dados de uma tarefa específica.
    """
    task = service.get_task(project_id, user_id, task_name)
    return to_task_response(task)


# --------------------------------------------------
# Task lifecycle (time tracking)
# --------------------------------------------------

@router.post("/{task_name}/start")
def start_task(
    project_id: int = Path(..., gt=0),
    task_name: str = Path(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Inicia contagem de tempo da tarefa.
    """
    service.start_task(project_id, user_id, task_name)
    return {"status": "started"}


@router.post("/{task_name}/stop")
def stop_task(
    project_id: int = Path(..., gt=0),
    task_name: str = Path(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Para contagem de tempo da tarefa.
    """
    duration_seconds = service.stop_task(project_id, user_id, task_name)
    return {
        "status": "stopped",
        "duration_seconds": duration_seconds,
    }


# --------------------------------------------------
# Complete Task
# --------------------------------------------------

@router.post("/{task_name}/complete")
def complete_task(
    project_id: int = Path(..., gt=0),
    task_name: str = Path(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Marca a tarefa como concluída.
    """
    service.complete_task(project_id, user_id, task_name)
    return {"status": "completed"}


# --------------------------------------------------
# Delete Task
# --------------------------------------------------

@router.delete("/{task_name}")
def delete_task(
    project_id: int = Path(..., gt=0),
    task_name: str = Path(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Exclui uma tarefa do projeto.
    """
    service.delete_task(project_id, user_id, task_name)
    return {"status": "deleted"}


# --------------------------------------------------
# Time Entries
# --------------------------------------------------

@router.get("/{task_name}/time-entries")
def list_time_entries(
    project_id: int = Path(..., gt=0),
    task_name: str = Path(..., min_length=1, max_length=TASK_NAME_MAX_LENGTH),
    service: TaskService = Depends(get_task_service),
    user_id: str = Depends(get_current_user_id),
):
    """
    Lista os intervalos de tempo registrados para a tarefa.
    """
    entries = service.get_time_entries(project_id, user_id, task_name)
    return [
        {
            "start_time": start,
            "end_time": end,
        }
        for start, end in entries
    ]
