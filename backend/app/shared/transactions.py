"""Transaction coordination contracts shared by application services."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol


class UnitOfWork(Protocol):
    """The transaction boundary used by one application operation."""

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@contextmanager
def atomic(unit_of_work: UnitOfWork) -> Iterator[None]:
    """Commit once on success and restore the transaction on any failure."""
    try:
        yield
        unit_of_work.commit()
    except Exception:
        unit_of_work.rollback()
        raise
