from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.modules.auth.model import User
from app.modules.payment_methods.schema import PaymentMethodCreate, PaymentMethodResponse, PaymentMethodUpdate
from app.modules.payment_methods.service import create_payment_method, delete_payment_method, list_payment_methods, update_payment_method
from app.shared.auth import get_current_user
from app.shared.dependencies import get_db
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(tags=["Meios de pagamento"])


@router.get("", response_model=list[PaymentMethodResponse])
def get_payment_methods(
    include_deleted: bool = Query(False),
    database: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_payment_methods(database, user.id, include_deleted)


@router.post("", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
def post_payment_method(data: PaymentMethodCreate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return create_payment_method(database, user.id, data.name)
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{method_id}", response_model=PaymentMethodResponse)
def put_payment_method(method_id: int, data: PaymentMethodUpdate, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return update_payment_method(database, method_id, user.id, data.name)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_payment_method(method_id: int, database: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        delete_payment_method(database, method_id, user.id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
