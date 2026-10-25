"""SQLAlchemy implementation of the application's transaction contract."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.shared.exceptions import PersistenceConflictError


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            raise PersistenceConflictError(
                "A database uniqueness constraint was violated."
            ) from error

    def rollback(self) -> None:
        self._session.rollback()
