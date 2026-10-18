from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.payment_methods.model import PaymentMethod


def list_payment_methods(database: Session) -> list[PaymentMethod]:
    """Retorna os meios de pagamento em ordem alfabética."""
    statement = select(PaymentMethod).order_by(PaymentMethod.name)
    return list(database.scalars(statement))
