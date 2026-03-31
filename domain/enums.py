from enum import Enum


# ---------------------------------------------------------
# Tipos de Projeto
# ---------------------------------------------------------

class ProjectType(str, Enum):
    LAYOUT = "LAYOUT"
    EXPORTACAO = "EXPORTACAO"
    NORMATIZACAO = "NORMATIZACAO"
    MAPEAMENTO = "MAPEAMENTO"
    MELHORIA = "MELHORIA"
    PECAS = "PECAS"


# ---------------------------------------------------------
# Classificação GUT
# ---------------------------------------------------------

class Severity(str, Enum):
    NONE = "Sem gravidade"
    LOW = "Pouco grave"
    MEDIUM = "Grave"
    HIGH = "Muito grave"
    CRITICAL = "Gravíssimo"


class Urgency(str, Enum):
    CAN_WAIT = "Pode esperar"
    LOW = "Pouco urgente"
    MEDIUM = "Urgente"
    FAST = "Mais rápido possível"
    IMMEDIATE = "Imediatamente"


class Trend(str, Enum):
    STABLE = "Não tende a piorar"
    LONG_TERM = "Piora em longo prazo"
    MEDIUM_TERM = "Piora em médio prazo"
    SHORT_TERM = "Piora em curto prazo"
    RAPID = "Piora rapidamente"


# ---------------------------------------------------------
# Clareza dos Objetivos
# ---------------------------------------------------------

class ObjectiveClarity(str, Enum):
    FULLY_DEFINED = "Objetivo totalmente definido"
    CLEAR_WITH_AMBIGUITIES = "Objetivo claro com pequenas ambiguidades"
    PARTIALLY_DEFINED = "Objetivo parcialmente definido"
    UNCLEAR = "Objetivo pouco claro"
    UNDEFINED = "Objetivo indefinido ou exploratório"


# ---------------------------------------------------------
# Clareza dos Métodos
# ---------------------------------------------------------

class MethodClarity(str, Enum):
    FULLY_DEFINED = "Métodos totalmente definidos e dominados"
    KNOWN_WITH_ADAPTATIONS = "Métodos conhecidos com pequenas adaptações"
    PARTIALLY_KNOWN = "Métodos parcialmente conhecidos"
    POORLY_DEFINED = "Métodos pouco definidos"
    UNKNOWN = "Métodos desconhecidos ou inexistentes"


# ---------------------------------------------------------
# Status das tarefas
# ---------------------------------------------------------

class TaskStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"