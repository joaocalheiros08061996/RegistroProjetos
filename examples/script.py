from datetime import datetime, timedelta
from domain.entities import Project, Task
from domain.enums import ProjectType, Severity, Urgency, Trend

# cria projeto
proj = Project(
    name="Migração Layout Planta A",
    project_type=ProjectType.LAYOUT,
    responsible_login="johndoe",
    fte=0.5,
    planned_start=datetime(2026, 3, 1),
    planned_end=datetime(2026, 3, 31),
    severity=Severity.MEDIUM,
    urgency=Urgency.MEDIUM,
    trend=Trend.SHORT_TERM,
    estimated_cost=15000.0,
)

# adiciona tarefa
t1 = proj.start_new_task(
    name="Mapeamento de linhas",
    planned_start=datetime(2026, 3, 1),
    planned_end=datetime(2026, 3, 5),
    cost=1000.0,
)

# Inicia e para entradas (simula trabalho em dois dias)
t1.start(datetime(2026, 3, 1, 9, 0, 0))
t1.stop(datetime(2026, 3, 1, 12, 0, 0))  # 3 horas

t1.start(datetime(2026, 3, 2, 13, 0, 0))
t1.stop(datetime(2026, 3, 2, 17, 0, 0))  # 4 horas

print("T1 horas totais (dias):", t1.actual_time.total_seconds()/3600.0)
print("T1 % completo:", t1.percent_completed())

# percentual do projeto
print("Projeto %:", proj.percent_completed())
print("Dias reais do projeto:", proj.actual_days())
