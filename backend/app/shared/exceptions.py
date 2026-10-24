class ResourceNotFoundError(Exception):
    """Indica que um recurso esperado não foi encontrado."""


class DuplicateResourceError(Exception):
    """Indica que o nome ativo já está sendo usado pelo proprietário."""
