class ResourceNotFoundError(Exception):
    """Indica que um recurso esperado não foi encontrado."""


class DuplicateResourceError(Exception):
    """Indica que o nome ativo já está sendo usado pelo proprietário."""


class DomainValidationError(ValueError):
    """A aplicação rejeitou um comando por uma regra do domínio."""


class PersistenceConflictError(Exception):
    """A database constraint rejected a concurrent write."""
