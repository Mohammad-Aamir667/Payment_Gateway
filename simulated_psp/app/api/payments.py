
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.payment import (CreatePaymentRequest, ProviderPaymentResponse)
from app.services.provider_payment_service import ProviderPaymentService



router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)





@router.post(
    "",
    response_model=ProviderPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    request: CreatePaymentRequest,
    db: Session = Depends(get_db),
):
    service = ProviderPaymentService(db)

    return await service.create_payment(
        gateway_payment_id=request.gateway_payment_id,
        amount=request.amount,
        currency=request.currency,
        scenario=request.scenario,
    )

@router.get(
    "/by-gateway/{gateway_payment_id}",
    response_model=ProviderPaymentResponse,
)
async def get_payment_by_gateway_id(
    gateway_payment_id: str,
    db: Session = Depends(get_db),
):
    service = ProviderPaymentService(db)

    payment =await service.get_payment_by_gateway_id(
        gateway_payment_id
    )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider payment not found.",
        )

    return payment


@router.get(
    "/{provider_payment_id}",
    response_model=ProviderPaymentResponse,
)
async def get_payment(
    provider_payment_id: str,
    db: Session = Depends(get_db),
):
    service = ProviderPaymentService(db)

    payment =await service.get_payment(
        provider_payment_id
    )

    if payment is None:
        HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider payment not found.",
        )

    return payment