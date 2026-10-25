from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.modules.auth.dependencies import get_current_user_id
from app.modules.payment_methods.dependencies import get_payment_method_service
from app.modules.payment_methods.schema import (
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodUpdate,
)
from app.modules.payment_methods.service import PaymentMethodService
from app.shared.exceptions import DuplicateResourceError, ResourceNotFoundError

router = APIRouter(tags=["Meios de pagamento"])


@router.get("", response_model=list[PaymentMethodResponse])
def get_payment_methods(
    include_deleted: bool = Query(False),
    service: PaymentMethodService = Depends(get_payment_method_service),
    user_id: UUID = Depends(get_current_user_id),
):
    return service.list(user_id, include_deleted)


@router.post("", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
def post_payment_method(
    data: PaymentMethodCreate,
    service: PaymentMethodService = Depends(get_payment_method_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.create(user_id, data.name)
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/{method_id}", response_model=PaymentMethodResponse)
def put_payment_method(
    method_id: int,
    data: PaymentMethodUpdate,
    service: PaymentMethodService = Depends(get_payment_method_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        return service.update(method_id, user_id, data.name)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DuplicateResourceError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_payment_method(
    method_id: int,
    service: PaymentMethodService = Depends(get_payment_method_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        service.delete(method_id, user_id)
    except ResourceNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
