from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modules.payment_methods.schema import PaymentMethodResponse
from app.modules.payment_methods.service import list_payment_methods
from app.shared.dependencies import get_db

router = APIRouter(tags=["Meios de pagamento"])


@router.get("", response_model=list[PaymentMethodResponse])
def get_payment_methods(database: Session = Depends(get_db)) -> list[PaymentMethodResponse]:
    return list_payment_methods(database)
