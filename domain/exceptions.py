class DomainError(Exception):
    """Base exception for domain errors."""


class ValidationError(DomainError):
    """Violação de regra invariável do domínio."""
    pass


class TaskAlreadyStartedError(DomainError):
    """Tentativa de iniciar uma tarefa já em andamento."""
    pass


class TaskNotStartedError(DomainError):
    """Tentativa de parar uma tarefa que não foi iniciada."""
    pass


class TaskAlreadyCompletedError(DomainError):
    """Tentativa de modificar uma tarefa já concluída."""
    pass


class InvalidOperationError(DomainError):
    """
    Operação semanticamente inválida para o estado atual da entidade.
    Usar apenas quando nenhuma exceção mais específica se aplica.
    """
    pass