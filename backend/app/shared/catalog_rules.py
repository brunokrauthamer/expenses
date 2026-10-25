"""Pure name rules shared by reference catalog use cases."""

from app.shared.exceptions import DomainValidationError


def normalize_catalog_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise DomainValidationError("O nome não pode ficar vazio.")
    if len(value) > 50:
        raise DomainValidationError("O nome pode ter no máximo 50 caracteres.")
    return value
